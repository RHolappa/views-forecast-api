"""Parquet-backed implementation of the forecast repository."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from cachetools import TTLCache

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
from app.services.sample_data import generate_sample_forecasts

logger = logging.getLogger(__name__)


class ParquetForecastRepository(ForecastRepository):
    """Load forecasts from local parquet files with light caching."""

    def __init__(self, data_path: Optional[str | Path] = None):
        self.cache = TTLCache(maxsize=settings.cache_max_size, ttl=settings.cache_ttl_seconds)
        self.data_path = Path(data_path or settings.data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

    def _load_data(self) -> pd.DataFrame:
        cache_key = f"parquet::{self.data_path.resolve()}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        parquet_files = list(self.data_path.glob("*.parquet"))

        if not parquet_files:
            logger.info("No parquet files found in %s; ensuring sample data exists", self.data_path)
            ensure_local_data_ready(prompt_user=False)
            parquet_files = list(self.data_path.glob("*.parquet"))

        frames: List[pd.DataFrame] = []
        for file in parquet_files:
            try:
                frames.append(pd.read_parquet(file))
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Failed to load %s: %s", file, exc)

        if not frames:
            logger.warning("Falling back to generated sample data")
            df = self._create_sample_data()
        else:
            df = pd.concat(frames, ignore_index=True)

        self.cache[cache_key] = df
        return df

    def _create_sample_data(self) -> pd.DataFrame:
        df = generate_sample_forecasts()
        sample_file = self.data_path / "sample_data.parquet"
        df.to_parquet(sample_file, index=False)
        logger.info("Sample data written to %s", sample_file)
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


__all__ = ["ParquetForecastRepository"]
