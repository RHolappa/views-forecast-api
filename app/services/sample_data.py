"""Utilities for working with forecast parquet schemas and sample data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

import numpy as np
import pandas as pd
from pandera import Check, Column, DataFrameSchema

# Forecast schema shared by the API and data preparation scripts.
FORECAST_COLUMNS: List[str] = [
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

_NON_NEG_CHECK = Check(lambda s: (s >= 0).all(), element_wise=False)
_UNIT_INTERVAL_CHECK = Check(lambda s: ((s >= 0) & (s <= 1)).all(), element_wise=False)
_UN_M49_CHECK = Check(lambda s: s.astype(str).str.fullmatch(r"\d{3}").all(), element_wise=False)

FORECAST_SCHEMA = DataFrameSchema(
    {
        "grid_id": Column("int32", coerce=True),
        "latitude": Column("float32", coerce=True),
        "longitude": Column("float32", coerce=True),
        "country_id": Column(str, checks=_UN_M49_CHECK, coerce=True),
        "admin_1_id": Column(str, coerce=True, nullable=True),
        "admin_2_id": Column(str, coerce=True, nullable=True),
        "month": Column(str, coerce=True),
        "map": Column("float32", checks=_NON_NEG_CHECK, coerce=True),
        "ci_50_low": Column("float32", checks=_NON_NEG_CHECK, coerce=True),
        "ci_50_high": Column("float32", checks=_NON_NEG_CHECK, coerce=True),
        "ci_90_low": Column("float32", checks=_NON_NEG_CHECK, coerce=True),
        "ci_90_high": Column("float32", checks=_NON_NEG_CHECK, coerce=True),
        "ci_99_low": Column("float32", checks=_NON_NEG_CHECK, coerce=True),
        "ci_99_high": Column("float32", checks=_NON_NEG_CHECK, coerce=True),
        "prob_0": Column("float32", checks=_UNIT_INTERVAL_CHECK, coerce=True),
        "prob_1": Column("float32", checks=_UNIT_INTERVAL_CHECK, coerce=True),
        "prob_10": Column("float32", checks=_UNIT_INTERVAL_CHECK, coerce=True),
        "prob_100": Column("float32", checks=_UNIT_INTERVAL_CHECK, coerce=True),
        "prob_1000": Column("float32", checks=_UNIT_INTERVAL_CHECK, coerce=True),
        "prob_10000": Column("float32", checks=_UNIT_INTERVAL_CHECK, coerce=True),
    },
    strict=True,
    coerce=True,
)


@dataclass(frozen=True)
class SampleConfig:
    # Default UN M49 numeric country codes (zero-padded to 3 digits)
    countries: Sequence[str] = ("800", "404", "834", "231", "646", "108")
    months: Iterable[str] = tuple(pd.period_range("2024-01", periods=6, freq="M").astype(str))
    grids_per_country: int = 6
    seed: int = 1337


def _build_probabilities(rng: np.random.Generator, base_prob: np.ndarray) -> pd.DataFrame:
    """Generate monotonically decreasing exceedance probabilities."""

    # The exceedance ladder shrinks progressively so prob_10 <= prob_1, etc.
    prob_10 = np.clip(base_prob * rng.uniform(0.4, 0.8, size=base_prob.shape), 0.0, 1.0)
    prob_100 = np.clip(prob_10 * rng.uniform(0.3, 0.7, size=base_prob.shape), 0.0, 1.0)
    prob_1000 = np.clip(prob_100 * rng.uniform(0.2, 0.6, size=base_prob.shape), 0.0, 1.0)
    prob_10000 = np.clip(prob_1000 * rng.uniform(0.1, 0.4, size=base_prob.shape), 0.0, 1.0)

    return pd.DataFrame(
        {
            "prob_1": base_prob.astype(np.float32),
            "prob_10": prob_10.astype(np.float32),
            "prob_100": prob_100.astype(np.float32),
            "prob_1000": prob_1000.astype(np.float32),
            "prob_10000": prob_10000.astype(np.float32),
        }
    )


def generate_sample_forecasts(config: SampleConfig | None = None) -> pd.DataFrame:
    """Generate a synthetic forecast dataset compatible with the API schema."""

    config = config or SampleConfig()
    rng = np.random.default_rng(config.seed)

    records = []
    grid_id = 1

    months = list(config.months)
    for country in config.countries:
        # Random centroid offsets per country keep grids clustered.
        base_lat = rng.uniform(-15, 15)
        base_lon = rng.uniform(10, 45)

        for grid_offset in range(config.grids_per_country):
            lat = base_lat + rng.normal(scale=1.5)
            lon = base_lon + rng.normal(scale=1.5)
            admin_1 = f"{country}-ADM1-{grid_offset % 4:02d}"
            admin_2 = f"{country}-ADM2-{grid_offset % 8:02d}"

            # Draw latent MAP baseline per grid to keep series correlated.
            grid_scale = rng.gamma(shape=2.0, scale=4.0)

            base_probs = rng.beta(a=3.0, b=2.5, size=len(months))
            prob_frame = _build_probabilities(rng, base_probs)

            map_values = rng.gamma(shape=2.5, scale=grid_scale, size=len(months)).astype(np.float32)
            ci_90_span = rng.uniform(0.8, 1.6, size=len(months)) * np.sqrt(map_values + 1)
            ci_50_span = ci_90_span * 0.4
            ci_99_span = ci_90_span * 1.5

            ci_90_low = np.clip(map_values - ci_90_span.astype(np.float32), 0, None)
            ci_90_high = map_values + ci_90_span.astype(np.float32)
            ci_50_low = np.clip(map_values - ci_50_span.astype(np.float32), 0, None)
            ci_50_high = map_values + ci_50_span.astype(np.float32)
            ci_99_low = np.clip(map_values - ci_99_span.astype(np.float32), 0, None)
            ci_99_high = map_values + ci_99_span.astype(np.float32)

            for month_idx, month in enumerate(months):
                prob_row = prob_frame.iloc[month_idx]

                record = {
                    "grid_id": np.int32(grid_id),
                    "latitude": np.float32(lat),
                    "longitude": np.float32(lon),
                    "country_id": country,
                    "admin_1_id": admin_1,
                    "admin_2_id": admin_2,
                    "month": month,
                    "map": map_values[month_idx],
                    "ci_50_low": ci_50_low[month_idx],
                    "ci_50_high": ci_50_high[month_idx],
                    "ci_90_low": ci_90_low[month_idx],
                    "ci_90_high": ci_90_high[month_idx],
                    "ci_99_low": ci_99_low[month_idx],
                    "ci_99_high": ci_99_high[month_idx],
                    "prob_1": prob_row["prob_1"],
                    "prob_0": np.float32(1.0 - prob_row["prob_1"]),
                    "prob_10": prob_row["prob_10"],
                    "prob_100": prob_row["prob_100"],
                    "prob_1000": prob_row["prob_1000"],
                    "prob_10000": prob_row["prob_10000"],
                }
                records.append(record)

            grid_id += 1

    df = pd.DataFrame.from_records(records, columns=FORECAST_COLUMNS)
    return FORECAST_SCHEMA.validate(df, lazy=True)


def write_sample_forecasts(output_path: Path, config: SampleConfig | None = None) -> Path:
    """Generate and persist a sample forecast parquet file."""

    df = generate_sample_forecasts(config=config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    return output_path
