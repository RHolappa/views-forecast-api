#!/usr/bin/env python3
"""Convert forecast parquet files into a SQLite database."""

from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import pandas as pd
import pyarrow.parquet as pq

try:
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
except ModuleNotFoundError:  # pragma: no cover - boto3 optional for local workflows
    boto3 = None
    BotoCoreError = ClientError = Exception
    UNSIGNED = None
    Config = None

# Allow running the script directly (`python scripts/load_parquet_to_db.py`)
if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.services.data_initializer import ensure_local_data_ready
from app.services.db_utils import sqlite_path_from_url
from app.services.sample_data import FORECAST_COLUMNS, FORECAST_SCHEMA
from scripts.prepare_views_forecasts import prepare_forecast_dataframe


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        help="Directory containing parquet files. Defaults to DATA_PATH from settings.",
    )
    parser.add_argument(
        "--database-url",
        help="Database URL to write to (sqlite only). Defaults to DATABASE_URL from settings.",
    )
    parser.add_argument(
        "--mode",
        choices=("replace", "append"),
        default="replace",
        help="Whether to replace or append to the existing forecasts table.",
    )
    parser.add_argument(
        "--skip-if-exists",
        action="store_true",
        help="Skip loading when the database already contains forecast rows.",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Delete the SQLite file before loading new data.",
    )
    parser.add_argument(
        "--s3-bucket",
        help="S3 bucket to download parquet files from (defaults to CLOUD_BUCKET_NAME).",
    )
    parser.add_argument(
        "--s3-prefix",
        help="S3 prefix containing parquet files (defaults to CLOUD_DATA_PREFIX).",
    )
    parser.add_argument(
        "--s3-key",
        action="append",
        help="Specific S3 object key to download. Can be passed multiple times.",
    )

    return parser.parse_args(argv)


def collect_parquet_files(source_dir: Path) -> Iterable[Path]:
    return sorted(source_dir.glob("*.parquet"))


def download_from_s3(
    bucket: str,
    destination: Path,
    prefix: Optional[str] = None,
    keys: Optional[Sequence[str]] = None,
) -> List[Path]:
    if not boto3:
        raise ImportError(
            "boto3 is required to download data from S3. Install dependencies with `make install`."
        )

    destination.mkdir(parents=True, exist_ok=True)

    session_kwargs = {}
    if settings.cloud_bucket_region:
        session_kwargs["region_name"] = settings.cloud_bucket_region

    if settings.aws_access_key_id and settings.aws_secret_access_key:
        session_kwargs["aws_access_key_id"] = settings.aws_access_key_id
        session_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

    session = boto3.session.Session(**session_kwargs)
    credentials = session.get_credentials()

    if credentials:
        client = session.client("s3")
    else:
        client = session.client("s3", config=Config(signature_version=UNSIGNED))

    object_keys: List[str] = []

    if keys:
        object_keys.extend(keys)

    normalized_prefix = prefix.lstrip("/") if prefix is not None else None

    if normalized_prefix is not None:
        paginator = client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=bucket, Prefix=normalized_prefix)

        for page in page_iterator:
            for obj in page.get("Contents", []):
                key = obj.get("Key")
                if key and key.endswith(".parquet"):
                    object_keys.append(key)

    if not object_keys:
        raise SystemExit(
            "No parquet objects found in S3. Adjust --s3-prefix/--s3-key or ensure the bucket contains data."
        )

    downloaded: List[Path] = []
    for key in sorted(set(object_keys)):
        local_path = destination / Path(key).name
        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            client.download_file(bucket, key, str(local_path))
        except (ClientError, BotoCoreError) as exc:
            raise SystemExit(f"Failed to download s3://{bucket}/{key}: {exc}") from exc

        downloaded.append(local_path)

    if not downloaded:
        raise SystemExit("No parquet files were downloaded from S3.")

    print(
        f"Downloaded {len(downloaded)} parquet file(s) from s3://{bucket}/"
        f"{normalized_prefix or ''} into {destination}"
    )
    return downloaded


def load_parquet_frames(parquet_files: Iterable[Path]) -> pd.DataFrame:
    df = build_forecast_dataframe(list(parquet_files))
    df = normalize_forecast_frame(df)
    df = FORECAST_SCHEMA.validate(df, lazy=True)
    return df[FORECAST_COLUMNS]


def build_forecast_dataframe(parquet_files: List[Path]) -> pd.DataFrame:
    if not parquet_files:
        raise FileNotFoundError("No parquet files found to load")

    by_type = {"api_ready": [], "raw_preds": [], "raw_hdi": [], "unknown": []}

    for path in parquet_files:
        file_type = classify_parquet_file(path)
        by_type[file_type].append(path)

    if by_type["api_ready"]:
        frames = [pd.read_parquet(path) for path in by_type["api_ready"]]
        return pd.concat(frames, ignore_index=True)

    if by_type["raw_preds"] and by_type["raw_hdi"]:
        hdi_index = {_raw_key(path): path for path in by_type["raw_hdi"]}
        prepared_frames: List[pd.DataFrame] = []

        for preds_path in by_type["raw_preds"]:
            key = _raw_key(preds_path)
            hdi_path = hdi_index.get(key)
            if not hdi_path:
                raise SystemExit(
                    f"No matching _90_hdi parquet found for raw predictions file {preds_path.name}"
                )

            prepared_frames.append(prepare_forecast_dataframe(preds_path, hdi_path))

        return pd.concat(prepared_frames, ignore_index=True)

    raise SystemExit(
        "Unable to determine parquet format. Provide API-ready parquet files or "
        "a matching pair of raw preds and *_90_hdi parquets."
    )


def classify_parquet_file(path: Path) -> str:
    try:
        schema = pq.read_schema(path)
    except Exception as exc:  # pragma: no cover - defensive
        raise SystemExit(f"Unable to read parquet schema for {path}: {exc}") from exc

    column_names = set(schema.names)

    if {"grid_id", "month", "map"}.issubset(column_names):
        return "api_ready"

    if "pred_ln_sb_best" in column_names:
        return "raw_preds"

    if {"pred_ln_sb_best_hdi_lower", "pred_ln_sb_best_hdi_upper"}.issubset(column_names):
        return "raw_hdi"

    return "unknown"


def _raw_key(path: Path) -> str:
    stem = path.stem
    if stem.endswith("_90_hdi"):
        stem = stem[: -len("_90_hdi")]
    return stem


def normalize_forecast_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce known columns into the expected schema before validation."""

    if "country_id" in df.columns:
        # Normalize country identifiers to zero-padded UN M49 codes when numeric.
        country_series = df["country_id"].astype("object")

        non_null_mask = country_series.notna()
        non_null_values = country_series[non_null_mask].astype(str).str.strip()
        non_null_values = non_null_values.str.replace(r"\.0$", "", regex=True)
        non_null_values = non_null_values.apply(
            lambda value: value.zfill(3) if value.isdigit() else value
        )

        invalid_mask = ~non_null_values.str.fullmatch(r"\d{3}")
        if invalid_mask.any():
            sample = non_null_values[invalid_mask].unique()[:5]
            raise ValueError(
                "Encountered non UN M49 country identifiers. Sample values: "
                f"{', '.join(sample)}"
            )

        country_series.loc[non_null_mask] = non_null_values
        df["country_id"] = country_series

    return df


def database_has_rows(conn: sqlite3.Connection) -> bool:
    try:
        cursor = conn.execute("SELECT 1 FROM forecasts LIMIT 1")
    except sqlite3.OperationalError:
        return False

    return cursor.fetchone() is not None


def create_indexes(conn: sqlite3.Connection) -> None:
    indexes = (
        "CREATE INDEX IF NOT EXISTS idx_forecasts_month ON forecasts(month)",
        "CREATE INDEX IF NOT EXISTS idx_forecasts_country ON forecasts(country_id)",
        "CREATE INDEX IF NOT EXISTS idx_forecasts_grid ON forecasts(grid_id)",
    )

    for statement in indexes:
        conn.execute(statement)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    if args.source and (args.s3_key or args.s3_prefix or args.s3_bucket):
        raise SystemExit("Use either --source or the S3 options, not both.")

    database_url = args.database_url or settings.database_url
    temp_dir: Optional[tempfile.TemporaryDirectory] = None

    try:
        explicit_s3 = bool(args.s3_bucket or args.s3_prefix or args.s3_key)
        auto_s3 = (
            args.source is None
            and not explicit_s3
            and bool(settings.cloud_bucket_name)
            and bool(settings.cloud_data_key or settings.cloud_data_prefix)
        )

        if explicit_s3 or auto_s3:
            bucket = args.s3_bucket or settings.cloud_bucket_name
            if not bucket:
                raise SystemExit(
                    "S3 bucket is required. Provide --s3-bucket or set CLOUD_BUCKET_NAME in .env."
                )

            prefix: Optional[str]
            if args.s3_prefix is not None:
                prefix = args.s3_prefix
            else:
                prefix = settings.cloud_data_prefix

            keys = args.s3_key
            if not keys and settings.cloud_data_key:
                keys = [settings.cloud_data_key]

            temp_dir = tempfile.TemporaryDirectory()
            temp_path = Path(temp_dir.name)
            parquet_files = download_from_s3(bucket, temp_path, prefix=prefix, keys=keys)
        else:
            source_dir = (args.source or Path(settings.data_path)).expanduser()

            if args.source is None:
                # Ensure a sample parquet exists for local workflows.
                ensure_local_data_ready(prompt_user=False)

            parquet_files = list(collect_parquet_files(source_dir))

            if not parquet_files:
                raise SystemExit(
                    f"No parquet files found under {source_dir}. "
                    "Provide --source or configure S3 settings to download data."
                )

        df = load_parquet_frames(parquet_files)
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()

    db_path = sqlite_path_from_url(database_url)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if args.reset_db and db_path.exists():
        db_path.unlink()
        print(f"Removed existing database at {db_path}")

    with sqlite3.connect(db_path) as conn:
        if args.skip_if_exists and database_has_rows(conn):
            print(f"Database at {db_path} already populated; skipping load.")
            return

        # Pandas will create the table schema for us when writing.
        df.to_sql("forecasts", conn, if_exists=args.mode, index=False)
        create_indexes(conn)

        row_count = conn.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0]

    print(
        f"Loaded {len(df):,} rows into {db_path} (table=forecasts). "
        f"Database now holds {row_count:,} rows."
    )


if __name__ == "__main__":
    main(sys.argv[1:])
