#!/usr/bin/env python3
"""Convert raw VIEWS forecast drops into parquet files the API can read."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

FORECAST_COLUMNS: list[str] = [
    "grid_id",
    "latitude",
    "longitude",
    "country_id",
    "admin_1_id",
    "admin_2_id",
    "month",
    "map",
    "ci_50_low",
    "ci_50_high",
    "ci_90_low",
    "ci_90_high",
    "ci_99_low",
    "ci_99_high",
    "prob_0",
    "prob_1",
    "prob_10",
    "prob_100",
    "prob_1000",
    "prob_10000",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare VIEWS forecasts for the API")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/views_raw/2025/07"),
        help="Directory containing the downloaded VIEWS CSV drops",
    )
    parser.add_argument(
        "--codebook",
        type=Path,
        default=None,
        help="Path to the VIEWS codebook JSON (defaults to <raw-dir>/codebook.json)",
    )
    parser.add_argument(
        "--priogrid-lookup",
        type=Path,
        default=None,
        help=(
            "CSV with PRIO-GRID metadata (pg_id, latitude, longitude, country_id, "
            "optional admin levels). Required for pgm conversion."
        ),
    )
    parser.add_argument(
        "--country-centroids",
        type=Path,
        default=None,
        help=(
            "CSV providing country_id and representative latitude/longitude; required if "
            "converting country-month aggregates."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/views_parquet/2025/07"),
        help="Directory where parquet files will be written",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow existing parquet files to be overwritten",
    )
    return parser.parse_args()


def build_month_lookup(codebook_path: Path) -> dict[int, str]:
    if not codebook_path.exists():
        raise FileNotFoundError(f"Codebook not found at {codebook_path}")

    with codebook_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    months = data.get("months") if isinstance(data, dict) else None
    if months is None:
        raise ValueError("Expected 'months' array in codebook JSON")

    lookup: dict[int, str] = {}
    for entry in months:
        try:
            month_id = int(entry.get("id"))
        except (TypeError, ValueError) as exc:  # pragma: no cover - guardrails
            raise ValueError(f"Invalid month id entry: {entry}") from exc
        name = entry.get("name") or entry.get("label")
        if not name:
            raise ValueError(f"Missing month name for id {month_id}")
        lookup[month_id] = name
    logger.info("Loaded %d month mappings from codebook", len(lookup))
    return lookup


def load_priogrid_lookup(path: Path | None) -> pd.DataFrame | None:
    if path is None:
        logger.warning("No PRIO-GRID lookup supplied; pgm conversion will be skipped")
        return None
    if not path.exists():
        raise FileNotFoundError(f"PRIO-GRID lookup not found at {path}")

    df = pd.read_csv(path)

    rename_map = {}
    if "pg_id" in df.columns:
        rename_map["pg_id"] = "grid_id"
    elif "gid" in df.columns:
        rename_map["gid"] = "grid_id"

    if "lat" in df.columns:
        rename_map["lat"] = "latitude"
    if "latitude" not in rename_map and "Latitude" in df.columns:
        rename_map["Latitude"] = "latitude"

    if "lon" in df.columns:
        rename_map["lon"] = "longitude"
    if "longitude" not in rename_map and "Longitude" in df.columns:
        rename_map["Longitude"] = "longitude"

    if "iso3" in df.columns:
        rename_map["iso3"] = "country_id"
    if "country" in df.columns and "country_id" not in rename_map:
        rename_map["country"] = "country_id"

    df = df.rename(columns=rename_map)

    required = {"grid_id", "latitude", "longitude", "country_id"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"PRIO-GRID lookup must contain columns {sorted(required)}; missing {sorted(missing)}"
        )

    subset_cols = ["grid_id", "latitude", "longitude", "country_id"]
    for optional in ("admin_1_id", "admin_2_id"):
        if optional in df.columns:
            subset_cols.append(optional)

    df = df[subset_cols].drop_duplicates("grid_id")
    logger.info("Loaded %d PRIO-GRID rows", len(df))
    return df


def load_country_centroids(path: Path | None) -> pd.DataFrame | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"Country centroids not found at {path}")

    df = pd.read_csv(path)
    rename_map = {}
    if "iso3" in df.columns:
        rename_map["iso3"] = "country_id"
    if "lat" in df.columns:
        rename_map["lat"] = "latitude"
    if "lon" in df.columns:
        rename_map["lon"] = "longitude"
    df = df.rename(columns=rename_map)

    required = {"country_id", "latitude", "longitude"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Country centroids CSV must include {sorted(required)}; missing {sorted(missing)}"
        )
    return df[["country_id", "latitude", "longitude"]]


def ensure_metric_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["map"] = df["map"].fillna(0)
    df["prob_1"] = df["prob_1"].clip(lower=0, upper=1).fillna(0)

    if "prob_0" not in df.columns:
        df["prob_0"] = (1 - df["prob_1"]).clip(lower=0, upper=1)

    for col in ("prob_10", "prob_100", "prob_1000", "prob_10000"):
        if col not in df.columns:
            df[col] = 0.0

    if "ci_50_low" not in df.columns:
        df["ci_50_low"] = df["map"] * 0.75
    if "ci_50_high" not in df.columns:
        df["ci_50_high"] = df["map"] * 1.25
    if "ci_90_low" not in df.columns:
        df["ci_90_low"] = df["map"] * 0.5
    if "ci_90_high" not in df.columns:
        df["ci_90_high"] = df["map"] * 1.5
    if "ci_99_low" not in df.columns:
        df["ci_99_low"] = df["map"] * 0.25
    if "ci_99_high" not in df.columns:
        df["ci_99_high"] = df["map"] * 2.0

    for col in (
        "ci_50_low",
        "ci_50_high",
        "ci_90_low",
        "ci_90_high",
        "ci_99_low",
        "ci_99_high",
    ):
        df[col] = df[col].fillna(0).clip(lower=0)

    return df


def reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in FORECAST_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[FORECAST_COLUMNS]


def convert_priogrid(
    csv_path: Path,
    output_path: Path,
    month_lookup: dict[int, str],
    priogrid_lookup: pd.DataFrame,
    overwrite: bool,
) -> Path:
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"{output_path} already exists. Use --overwrite to replace it.")

    logger.info("Processing PRIO-GRID file %s", csv_path)
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError(f"Input file {csv_path} has no rows")

    df = df.rename(
        columns={
            "pg_id": "grid_id",
            "main_mean": "map",
            "main_dich": "prob_1",
        }
    )
    required = {"grid_id", "month_id", "map", "prob_1"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing expected columns in {csv_path}: {sorted(missing)}")

    df["month"] = df["month_id"].map(month_lookup)
    if df["month"].isna().any():
        bad_ids = df.loc[df["month"].isna(), "month_id"].unique()
        raise ValueError(f"Month IDs {bad_ids} not found in codebook")

    df = df.merge(priogrid_lookup, on="grid_id", how="left")
    if df[["latitude", "longitude"]].isna().any().any():
        missing = df.loc[df["latitude"].isna(), "grid_id"].unique()
        raise ValueError(
            f"Latitude/longitude missing for {len(missing)} grid cells. Check the PRIO-GRID lookup."
        )

    df = ensure_metric_columns(df)
    df = reorder_columns(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logger.info("Wrote %s (%d rows)", output_path, len(df))
    return output_path


def convert_country_month(
    csv_path: Path,
    output_path: Path,
    month_lookup: dict[int, str],
    centroids: pd.DataFrame,
    overwrite: bool,
) -> Path:
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"{output_path} already exists. Use --overwrite to replace it.")

    logger.info("Processing country-month file %s", csv_path)
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError(f"Input file {csv_path} has no rows")

    df = df.rename(
        columns={
            "main_mean": "map",
            "main_dich": "prob_1",
            "isoab": "country_id",
        }
    )

    required = {"country_id", "year", "month", "map", "prob_1"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing expected columns in {csv_path}: {sorted(missing)}")

    df["month"] = df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)
    if "month_id" in df.columns:
        df["codebook_month"] = df["month_id"].map(month_lookup)

    df = df.merge(centroids, on="country_id", how="left")
    if df[["latitude", "longitude"]].isna().any().any():
        missing = df.loc[df["latitude"].isna(), "country_id"].unique()
        raise ValueError(
            f"Centroid lookup missing latitude/longitude for countries {sorted(missing)}"
        )

    # Create synthetic grid ids so rows can co-exist with PRIO-GRID cells
    df = df.sort_values(["country_id", "month"])
    df["grid_id"] = (
        df["country_id"].astype("category").cat.codes.astype(int) + 10_000_000
    )

    df["admin_1_id"] = None
    df["admin_2_id"] = None

    df = ensure_metric_columns(df)
    df = reorder_columns(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logger.info("Wrote %s (%d rows)", output_path, len(df))
    return output_path


def main() -> None:
    args = parse_args()

    codebook_path = args.codebook or args.raw_dir / "codebook.json"
    month_lookup = build_month_lookup(codebook_path)

    priogrid_lookup = load_priogrid_lookup(args.priogrid_lookup)
    country_centroids = load_country_centroids(args.country_centroids)

    outputs: list[Path] = []

    pgm_files = sorted(args.raw_dir.glob("*_pgm.csv"))
    if pgm_files and priogrid_lookup is None:
        logger.error(
            "PRIO-GRID CSV found but no lookup provided. Supply --priogrid-lookup to convert pgm data."
        )
    for csv in pgm_files:
        if priogrid_lookup is None:
            continue
        out_name = csv.stem.replace("_t01", "") + "_pgm.parquet"
        output_path = args.output_dir / out_name
        outputs.append(
            convert_priogrid(csv, output_path, month_lookup, priogrid_lookup, args.overwrite)
        )

    cm_files = sorted(args.raw_dir.glob("*_cm.csv"))
    if cm_files and country_centroids is None:
        logger.warning(
            "Country-month CSV detected but no centroid lookup supplied; skipping cm conversion."
        )
    for csv in cm_files:
        if country_centroids is None:
            continue
        out_name = csv.stem.replace("_t01", "") + "_cm.parquet"
        output_path = args.output_dir / out_name
        outputs.append(
            convert_country_month(csv, output_path, month_lookup, country_centroids, args.overwrite)
        )

    if not outputs:
        logger.warning("No CSV files were converted. Check the --raw-dir contents.")
    else:
        logger.info("Conversion finished: %s", ", ".join(str(p) for p in outputs))


if __name__ == "__main__":
    main()
