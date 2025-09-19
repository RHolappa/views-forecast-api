#!/usr/bin/env python3
"""Convert VIEWS pipeline outputs into the API's parquet schema."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
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
    parser = argparse.ArgumentParser(description="Prepare parquet forecasts for the API")
    parser.add_argument(
        "--pgm-csv",
        type=Path,
        required=True,
        help="Path to fatalities*-pgm.csv (grid-level monthly forecasts)",
    )
    parser.add_argument(
        "--cm-csv",
        type=Path,
        required=True,
        help="Path to fatalities*-cm.csv (provides month_id to YYYY-MM mapping)",
    )
    parser.add_argument(
        "--preds-parquet",
        type=Path,
        required=True,
        help="Path to preds_*.parquet containing grid coordinates",
    )
    parser.add_argument(
        "--hdi-parquet",
        type=Path,
        required=True,
        help="Path to preds_*_90_hdi.parquet providing 90% intervals",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/views_parquet/2025/07/forecasts.parquet"),
        help="Output parquet file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it exists",
    )
    return parser.parse_args()


def build_month_and_country_lookups(cm_csv: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(cm_csv, usecols=["month_id", "year", "month", "gwcode", "isoab"])

    month_df = (
        df.drop_duplicates("month_id")
        .assign(month=lambda d: d["year"].astype(str) + "-" + d["month"].astype(str).str.zfill(2))
        [["month_id", "month"]]
    )

    country_df = df.drop_duplicates("gwcode")[["gwcode", "isoab"]]
    country_df["gwcode"] = country_df["gwcode"].astype(int)
    country_df = country_df.rename(columns={"isoab": "iso_alpha3"})

    return month_df, country_df


def load_preds(parquet_path: Path) -> pd.DataFrame:
    df = pd.read_parquet(parquet_path).reset_index()
    df = df.rename(
        columns={
            "priogrid_id": "grid_id",
            "lat": "latitude",
            "lon": "longitude",
            "country_id": "gwcode",
        }
    )
    df["gwcode"] = df["gwcode"].astype(int)
    keep = ["grid_id", "latitude", "longitude", "gwcode"]
    return df[keep].drop_duplicates("grid_id")


def load_hdi(parquet_path: Path) -> pd.DataFrame:
    df = pd.read_parquet(parquet_path).reset_index()
    df = df.rename(columns={"priogrid_id": "grid_id"})
    keep = [
        "month_id",
        "grid_id",
        "pred_ln_sb_best_hdi_lower",
        "pred_ln_sb_best_hdi_upper",
        "pred_ln_sb_prob_hdi_lower",
        "pred_ln_sb_prob_hdi_upper",
    ]
    missing = set(keep) - set(df.columns)
    if missing:
        raise ValueError(f"HDI parquet missing columns: {sorted(missing)}")
    return df[keep]


def compute_intervals(base: pd.DataFrame) -> pd.DataFrame:
    base = base.copy()
    base["ci_90_low"] = np.expm1(base["pred_ln_sb_best_hdi_lower"].fillna(0))
    base["ci_90_high"] = np.expm1(base["pred_ln_sb_best_hdi_upper"].fillna(0))

    # Derive 50% and 99% intervals from the 90% band if no direct values exist
    span_low = (base["map"] - base["ci_90_low"]).clip(lower=0)
    span_high = (base["ci_90_high"] - base["map"]).clip(lower=0)

    base["ci_50_low"] = (base["map"] - 0.5 * span_low).clip(lower=0)
    base["ci_50_high"] = base["map"] + 0.5 * span_high
    base["ci_99_low"] = (base["map"] - 1.5 * span_low).clip(lower=0)
    base["ci_99_high"] = base["map"] + 1.5 * span_high

    return base


def main() -> None:
    args = parse_args()

    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"{args.output} already exists. Use --overwrite to replace it.")

    logger.info("Loading grid-level forecasts from %s", args.pgm_csv)
    pgm_df = pd.read_csv(args.pgm_csv)
    expected = {"pg_id", "month_id", "main_mean", "main_dich"}
    missing = expected - set(pgm_df.columns)
    if missing:
        raise ValueError(f"PGM CSV missing columns: {sorted(missing)}")

    month_lookup, country_lookup = build_month_and_country_lookups(args.cm_csv)
    preds_df = load_preds(args.preds_parquet)
    hdi_df = load_hdi(args.hdi_parquet)

    df = (
        pgm_df.merge(month_lookup, on="month_id", how="left")
        .merge(preds_df, how="left", left_on="pg_id", right_on="grid_id")
        .merge(hdi_df, how="left", on=["month_id", "grid_id"])
    )

    if df["month"].isna().any():
        missing_months = df.loc[df["month"].isna(), "month_id"].unique()
        raise ValueError(f"No month mapping found for month_id(s): {missing_months}")

    if df["latitude"].isna().any() or df["longitude"].isna().any():
        missing_cells = df.loc[df["latitude"].isna(), "grid_id"].unique()
        raise ValueError(
            f"Latitude/longitude missing for grid cell(s): {sorted(missing_cells)}. Check preds parquet."
        )

    df = df.drop(columns=["pg_id"], errors="ignore")
    df = df.merge(country_lookup, how="left", left_on="gwcode", right_on="gwcode")
    df["country_id"] = df["iso_alpha3"]
    mask_missing_iso = df["country_id"].isna()
    if mask_missing_iso.any():
        logger.warning(
            "ISO alpha-3 code missing for %d GW codes; falling back to zero-padded GW codes",
            mask_missing_iso.sum(),
        )
        df.loc[mask_missing_iso, "country_id"] = (
            df.loc[mask_missing_iso, "gwcode"].astype(int).astype(str).str.zfill(3)
        )
    df["country_id"] = df["country_id"].astype(str)
    df = df.drop(columns=["iso_alpha3", "gwcode"], errors="ignore")
    df["grid_id"] = df["grid_id"].astype(int)
    df["admin_1_id"] = None
    df["admin_2_id"] = None
    df["map"] = df["main_mean"].clip(lower=0)
    df["prob_1"] = df["main_dich"].clip(lower=0, upper=1)
    df["prob_0"] = (1 - df["prob_1"]).clip(lower=0, upper=1)

    df = compute_intervals(df)

    # Probabilities for higher fatality thresholds are not provided; set conservative defaults.
    for col in ("prob_10", "prob_100", "prob_1000", "prob_10000"):
        df[col] = 0.0

    df = df[FORECAST_COLUMNS]
    df = df.sort_values(["month", "grid_id"]).reset_index(drop=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.output, index=False)
    logger.info("Wrote %s (%d rows)", args.output, len(df))


if __name__ == "__main__":
    main()
