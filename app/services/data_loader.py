"""Forecast repository with support for multiple storage backends."""

from __future__ import annotations

import logging
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import pyarrow.parquet as pq
from cachetools import TTLCache

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ModuleNotFoundError:  # pragma: no cover - boto3 optional for local workflows
    boto3 = None
    BotoCoreError = ClientError = Exception

from app.core.config import settings
from app.domain.repositories import ForecastRepository
from app.models.forecast import (
    ALL_METRIC_NAMES,
    ComparisonOperator,
    ForecastMetrics,
    GridCellForecast,
    MetricConstraint,
    MetricName,
)
from app.services.data_initializer import ensure_local_data_ready
from app.services.db_utils import sqlite_path_from_url
from app.services.sample_data import FORECAST_COLUMNS, generate_sample_forecasts

logger = logging.getLogger(__name__)


class DataLoader(ForecastRepository):
    """Load forecast data from parquet, SQLite, or cloud storage."""

    def __init__(
        self,
        *,
        data_path: Optional[str | Path] = None,
        backend: Optional[str] = None,
        database_url: Optional[str] = None,
    ) -> None:
        self.cache = TTLCache(maxsize=settings.cache_max_size, ttl=settings.cache_ttl_seconds)
        self.data_path = Path(data_path or settings.data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

        self.backend = (backend or settings.data_backend).lower()
        self._database_url = database_url or settings.database_url

        self._data: Optional[pd.DataFrame] = None
        self._s3_client = None
        self._db_path: Optional[Path] = None

        if self.backend == "cloud" and self._should_use_sample_backend():
            logger.warning(
                "Falling back to sample data because USE_LOCAL_DATA is true or AWS credentials are missing."
            )
            self.backend = "parquet"
            ensure_local_data_ready(prompt_user=False)

        if self.backend == "parquet":
            self.data_path.mkdir(parents=True, exist_ok=True)
        elif self.backend == "database":
            self._init_database()
        elif self.backend == "cloud":
            self._init_cloud_storage()
        else:
            raise ValueError(f"Unsupported data backend: {self.backend}")

    @staticmethod
    def _is_blank(value: Optional[str]) -> bool:
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        return False

    def _should_use_sample_backend(self) -> bool:
        if settings.use_local_data:
            return True
        if self._is_blank(settings.aws_access_key_id) or self._is_blank(
            settings.aws_secret_access_key
        ):
            return True
        return False

    def _init_database(self) -> None:
        try:
            self._db_path = sqlite_path_from_url(self._database_url)
        except ValueError as exc:  # pragma: no cover - configuration guard
            raise ValueError(f"Invalid DATABASE_URL '{self._database_url}': {exc}") from exc

        if not self._db_path.parent.exists():
            self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def _init_cloud_storage(self) -> None:
        if not boto3:
            raise ImportError(
                "boto3 is required for cloud data loading but is not installed. Install dependencies with `make install`."
            )
        if not settings.cloud_bucket_name:
            raise ValueError("CLOUD_BUCKET_NAME must be set when DATA_BACKEND=cloud")

        session = boto3.session.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.cloud_bucket_region,
        )
        self._s3_client = session.client("s3")

    def _load_data(self) -> pd.DataFrame:
        cache_key = f"all_data::{self.backend}::{self.data_path}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        if self.backend == "parquet":
            df = self._load_local_data()
        elif self.backend == "database":
            df = self._load_database_data()
        elif self.backend == "cloud":
            df = self._load_cloud_data()
        else:  # pragma: no cover - defensive
            raise ValueError(f"Unsupported data backend: {self.backend}")

        self.cache[cache_key] = df
        return df

    def _load_local_data(self) -> pd.DataFrame:
        parquet_files = list(self.data_path.glob("*.parquet"))

        if not parquet_files:
            logger.warning("No parquet files found in %s", self.data_path)
            ensure_local_data_ready(prompt_user=False)
            parquet_files = list(self.data_path.glob("*.parquet"))

        if not parquet_files:
            logger.error("Unable to locate parquet files; returning generated sample data.")
            return self._create_sample_data()

        frames: List[pd.DataFrame] = []
        for file in parquet_files:
            try:
                frames.append(pd.read_parquet(file))
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Error loading %s: %s", file, exc)

        if frames:
            return pd.concat(frames, ignore_index=True)
        return self._create_sample_data()

    def _load_database_data(self) -> pd.DataFrame:
        if not self._db_path:
            logger.error("Database path is not configured; returning empty DataFrame")
            return pd.DataFrame(columns=FORECAST_COLUMNS)

        if not self._db_path.exists():
            logger.warning(
                "SQLite database %s not found. Run `python scripts/load_parquet_to_db.py` or `make db-load` to populate it.",
                self._db_path,
            )
            return pd.DataFrame(columns=FORECAST_COLUMNS)

        try:
            with sqlite3.connect(self._db_path) as conn:
                df = pd.read_sql_query("SELECT * FROM forecasts", conn)
        except sqlite3.OperationalError as exc:
            logger.error("Failed to read forecasts table from %s: %s", self._db_path, exc)
            return pd.DataFrame(columns=FORECAST_COLUMNS)

        missing_columns = [col for col in FORECAST_COLUMNS if col not in df.columns]
        if missing_columns:
            logger.error(
                "Database %s is missing expected columns: %s",
                self._db_path,
                ", ".join(missing_columns),
            )
            return pd.DataFrame(columns=FORECAST_COLUMNS)

        return df[FORECAST_COLUMNS]

    def _resolve_object_keys(self, bucket: str) -> List[str]:
        if settings.cloud_data_key:
            return [settings.cloud_data_key]

        prefix = settings.cloud_data_prefix.strip("/") if settings.cloud_data_prefix else ""
        if prefix and not prefix.endswith("/"):
            prefix = f"{prefix}/"

        continuation_token = None
        keys: List[str] = []

        while True:
            try:
                list_kwargs: Dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
                if continuation_token:
                    list_kwargs["ContinuationToken"] = continuation_token
                response = self._s3_client.list_objects_v2(**list_kwargs)
            except (ClientError, BotoCoreError) as exc:
                logger.error("Failed to list objects in bucket %s: %s", bucket, exc)
                return []

            for obj in response.get("Contents", []):
                key = obj.get("Key")
                if key and key.endswith(".parquet"):
                    keys.append(key)

            if response.get("IsTruncated"):
                continuation_token = response.get("NextContinuationToken")
            else:
                break

        return keys

    def _classify_parquet_file(self, path: Path) -> str:
        try:
            schema = pq.read_schema(path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Unable to read parquet schema for %s: %s", path, exc)
            return "unknown"

        column_names = set(schema.names)

        if {"grid_id", "month", "map"}.issubset(column_names):
            return "api_ready"
        if "pred_ln_sb_best" in column_names:
            return "raw_preds"
        if {"pred_ln_sb_best_hdi_lower", "pred_ln_sb_best_hdi_upper"}.issubset(column_names):
            return "raw_hdi"
        return "unknown"

    @staticmethod
    def _raw_key(path: Path) -> str:
        stem = path.stem
        if stem.endswith("_90_hdi"):
            stem = stem[: -len("_90_hdi")]
        return stem

    def _prepare_raw_pair(self, preds_path: Path, hdi_path: Path) -> pd.DataFrame:
        scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.append(str(scripts_dir))

        # Local import to avoid circular dependencies at module import time.
        from prepare_views_forecasts import prepare_forecast_dataframe  # type: ignore

        return prepare_forecast_dataframe(preds_path, hdi_path)

    def _load_cloud_data(self) -> pd.DataFrame:
        if not self._s3_client:
            logger.error("S3 client is not initialized; returning generated sample data")
            return self._create_sample_data()

        bucket = settings.cloud_bucket_name
        object_keys = self._resolve_object_keys(bucket)

        if not object_keys:
            logger.warning(
                "No parquet objects found in bucket %s with prefix '%s'",
                bucket,
                settings.cloud_data_prefix,
            )
            return self._create_sample_data()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            by_type: Dict[str, List[Path]] = {
                "api_ready": [],
                "raw_preds": [],
                "raw_hdi": [],
                "unknown": [],
            }

            for key in object_keys:
                local_path = temp_path / Path(key).name
                try:
                    with local_path.open("wb") as fp:
                        self._s3_client.download_fileobj(bucket, key, fp)
                    file_type = self._classify_parquet_file(local_path)
                    by_type[file_type].append(local_path)
                    logger.info("Loaded %s from s3://%s/%s", local_path.name, bucket, key)
                except (ClientError, BotoCoreError) as exc:
                    logger.error("Failed to download %s from bucket %s: %s", key, bucket, exc)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.error("Failed to process parquet %s in bucket %s: %s", key, bucket, exc)

            if by_type["api_ready"]:
                frames = [pd.read_parquet(path) for path in by_type["api_ready"]]
                return pd.concat(frames, ignore_index=True)

            if by_type["raw_preds"] and by_type["raw_hdi"]:
                hdi_index = {self._raw_key(path): path for path in by_type["raw_hdi"]}
                prepared_frames: List[pd.DataFrame] = []

                for preds_path in by_type["raw_preds"]:
                    key = self._raw_key(preds_path)
                    hdi_path = hdi_index.get(key)
                    if not hdi_path:
                        logger.warning("No matching HDI parquet found for %s", preds_path.name)
                        continue

                    try:
                        prepared_frames.append(self._prepare_raw_pair(preds_path, hdi_path))
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.error(
                            "Failed to prepare raw parquet pair %s / %s: %s",
                            preds_path,
                            hdi_path,
                            exc,
                        )

                if prepared_frames:
                    return pd.concat(prepared_frames, ignore_index=True)

        logger.error(
            "Unable to load usable parquet data from cloud; returning generated sample data"
        )
        return self._create_sample_data()

    def _create_sample_data(self) -> pd.DataFrame:
        df = generate_sample_forecasts()
        sample_file = self.data_path / "sample_data.parquet"
        df.to_parquet(sample_file, index=False)
        logger.info("Sample data saved to %s", sample_file)
        return df

    def get_forecasts(
        self,
        country: Optional[str] = None,
        grid_ids: Optional[List[int]] = None,
        months: Optional[List[str]] = None,
        metrics: Optional[List[MetricName]] = None,
        metric_constraints: Optional[List[MetricConstraint]] = None,
    ) -> List[GridCellForecast]:
        df = self._load_data()

        if country:
            df = df[df["country_id"] == country]

        if grid_ids:
            df = df[df["grid_id"].isin(grid_ids)]

        if months:
            df = df[df["month"].isin(months)]

        if metric_constraints:
            for constraint in metric_constraints:
                column = constraint.metric.value
                if column not in df.columns:
                    raise ValueError(f"Metric '{column}' is not available for filtering")

                if constraint.operator is ComparisonOperator.gt:
                    df = df[df[column] > constraint.value]
                elif constraint.operator is ComparisonOperator.gte:
                    df = df[df[column] >= constraint.value]
                elif constraint.operator is ComparisonOperator.lt:
                    df = df[df[column] < constraint.value]
                elif constraint.operator is ComparisonOperator.lte:
                    df = df[df[column] <= constraint.value]

        selected_metrics = [metric.value for metric in metrics] if metrics else ALL_METRIC_NAMES

        forecasts: List[GridCellForecast] = []
        for _, row in df.iterrows():
            record = row.to_dict()
            metrics_data = {name: record[name] for name in selected_metrics if name in record}
            forecasts.append(
                GridCellForecast(
                    grid_id=int(record["grid_id"]),
                    latitude=float(record["latitude"]),
                    longitude=float(record["longitude"]),
                    country_id=str(record["country_id"]),
                    admin_1_id=record.get("admin_1_id"),
                    admin_2_id=record.get("admin_2_id"),
                    month=record["month"],
                    metrics=ForecastMetrics(**metrics_data),
                )
            )

        return forecasts

    def get_available_months(self) -> List[Dict[str, Any]]:
        df = self._load_data()

        months_data: List[Dict[str, Any]] = []
        for month in df["month"].unique():
            month_df = df[df["month"] == month]
            months_data.append(
                {
                    "month": month,
                    "forecast_count": len(month_df),
                    "countries": month_df["country_id"].unique().tolist(),
                }
            )

        return sorted(months_data, key=lambda item: item["month"])

    def get_grid_cells(self, country: Optional[str] = None) -> List[Dict[str, Any]]:
        df = self._load_data()

        if country:
            df = df[df["country_id"] == country]

        grouped = (
            df.groupby(["grid_id", "latitude", "longitude", "country_id"]).first().reset_index()
        )

        cells: List[Dict[str, Any]] = []
        for _, row in grouped.iterrows():
            cells.append(
                {
                    "grid_id": int(row["grid_id"]),
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "country_id": str(row["country_id"]),
                    "admin_1_id": row.get("admin_1_id"),
                    "admin_2_id": row.get("admin_2_id"),
                }
            )

        return cells


__all__ = ["DataLoader"]
