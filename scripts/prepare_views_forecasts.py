#!/usr/bin/env python3
"""Convert raw VIEWS forecast draws into the API's parquet schema."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from pandera import Check, Column, DataFrameSchema

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.sample_data import FORECAST_COLUMNS, FORECAST_SCHEMA

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_PERIOD = pd.Period("1990-01", freq="M")


def _is_array_like(value: object) -> bool:
    return isinstance(value, (list, tuple, np.ndarray))


ARRAY_LIKE_CHECK = Check(
    lambda s: s.apply(_is_array_like).all(),
    element_wise=False,
    error="pred_ln_sb_best column must contain array-like draws",
)

RAW_PRED_SCHEMA = DataFrameSchema(
    {
        "month_id": Column("int32", coerce=True),
        "priogrid_id": Column("int32", coerce=True),
        "country_id": Column("int32", coerce=True),
        "lat": Column("float64", coerce=True),
        "lon": Column("float64", coerce=True),
        "pred_ln_sb_best": Column(object, checks=ARRAY_LIKE_CHECK),
    },
    strict=False,
    coerce=True,
)


RAW_HDI_SCHEMA = DataFrameSchema(
    {
        "month_id": Column("int32", coerce=True),
        "priogrid_id": Column("int32", coerce=True),
        "pred_ln_sb_best_hdi_lower": Column("float64", coerce=True),
        "pred_ln_sb_best_hdi_upper": Column("float64", coerce=True),
    },
    strict=False,
    coerce=True,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare parquet forecasts for the API")
    parser.add_argument(
        "--preds-parquet",
        type=Path,
        required=True,
        help="Path to raw preds_*.parquet containing forecast draws",
    )
    parser.add_argument(
        "--hdi-parquet",
        type=Path,
        required=True,
        help="Path to raw preds_*_90_hdi.parquet",
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


def load_preds(parquet_path: Path) -> pd.DataFrame:
    df = pd.read_parquet(parquet_path).reset_index()
    df = RAW_PRED_SCHEMA.validate(df, lazy=True)
    df["pred_ln_sb_best"] = df["pred_ln_sb_best"].apply(
        lambda arr: np.asarray(arr, dtype=np.float32)
    )
    return df


def load_hdi(parquet_path: Path) -> pd.DataFrame:
    df = pd.read_parquet(parquet_path).reset_index()
    return RAW_HDI_SCHEMA.validate(df, lazy=True)


def month_id_to_month(month_ids: Iterable[int]) -> pd.Series:
    offsets = pd.Series(month_ids, dtype="int32") - 1
    return (BASE_PERIOD + offsets).astype(str)


def summarise_draws(draws: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[int, np.ndarray]]:
    linear = np.expm1(draws)
    quantiles = np.quantile(linear, [0.25, 0.75, 0.005, 0.995], axis=1)
    thresholds = {thr: (linear >= thr).mean(axis=1) for thr in (1, 10, 100, 1000, 10000)}
    return linear.mean(axis=1), quantiles, thresholds


def prepare_forecast_dataframe(preds_path: Path, hdi_path: Path) -> pd.DataFrame:
    preds_df = load_preds(preds_path)
    hdi_df = load_hdi(hdi_path)

    df = preds_df.merge(
        hdi_df,
        on=["month_id", "priogrid_id"],
        how="left",
        validate="one_to_one",
    )

    if df[["pred_ln_sb_best_hdi_lower", "pred_ln_sb_best_hdi_upper"]].isna().any().any():
        missing = df.loc[
            df["pred_ln_sb_best_hdi_lower"].isna() | df["pred_ln_sb_best_hdi_upper"].isna(),
            ["month_id", "priogrid_id"],
        ]
        pairs = ", ".join(f"({m}, {g})" for m, g in missing.itertuples(index=False))
        raise ValueError(f"Missing 90% interval bounds for grid cells: {pairs}")

    draws_matrix = np.stack(df["pred_ln_sb_best"].to_numpy())
    map_values, quantiles, threshold_probs = summarise_draws(draws_matrix)

    df["map"] = np.clip(map_values.astype(np.float32), a_min=0, a_max=None)
    df["ci_50_low"] = np.clip(quantiles[0].astype(np.float32), a_min=0, a_max=None)
    df["ci_50_high"] = quantiles[1].astype(np.float32)
    df["ci_99_low"] = np.clip(quantiles[2].astype(np.float32), a_min=0, a_max=None)
    df["ci_99_high"] = quantiles[3].astype(np.float32)

    df["ci_90_low"] = np.clip(
        np.expm1(df["pred_ln_sb_best_hdi_lower"].astype(np.float32)), a_min=0, a_max=None
    )
    df["ci_90_high"] = np.expm1(df["pred_ln_sb_best_hdi_upper"].astype(np.float32)).astype(
        np.float32
    )

    for threshold, probs in threshold_probs.items():
        col = f"prob_{threshold}"
        df[col] = np.clip(probs.astype(np.float32), a_min=0, a_max=1)

    df["prob_0"] = np.clip(1.0 - df["prob_1"], a_min=0, a_max=1).astype(np.float32)

    df["grid_id"] = df["priogrid_id"].astype(np.int32)
    df["latitude"] = df["lat"].astype(np.float32)
    df["longitude"] = df["lon"].astype(np.float32)
    df["country_id"] = df["country_id"].astype(np.int32).astype(str).str.zfill(3)
    df["admin_1_id"] = None
    df["admin_2_id"] = None
    df["month"] = month_id_to_month(df["month_id"].to_numpy())

    float_cols = [
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
    for col in float_cols:
        df[col] = df[col].astype(np.float32)

    result = df[FORECAST_COLUMNS].sort_values(["month", "grid_id"]).reset_index(drop=True)
    FORECAST_SCHEMA.validate(result, lazy=True)
    return result


def main() -> None:
    args = parse_args()

    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"{args.output} already exists. Use --overwrite to replace it.")

    logger.info("Preparing forecasts from %s and %s", args.preds_parquet, args.hdi_parquet)
    forecast_df = prepare_forecast_dataframe(args.preds_parquet, args.hdi_parquet)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    forecast_df.to_parquet(args.output, index=False)
    logger.info("Wrote %s (%d rows)", args.output, len(forecast_df))


if __name__ == "__main__":
    main()
