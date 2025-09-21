"""Core service for forecast data retrieval and processing."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from app.domain.repositories import ForecastRepository
from app.models.forecast import ForecastQuery, GridCellForecast, MetricName

logger = logging.getLogger(__name__)


class ForecastService:
    """Business logic for querying forecasts."""

    def __init__(self, repository: ForecastRepository):
        self.repository = repository

    def parse_month_range(self, month_range: str) -> List[str]:
        """Parse month range string into list of months."""
        parts = month_range.split(":")
        if len(parts) != 2:
            raise ValueError("Invalid month range format")

        start_date = datetime.strptime(f"{parts[0]}-01", "%Y-%m-%d")
        end_date = datetime.strptime(f"{parts[1]}-01", "%Y-%m-%d")

        if start_date > end_date:
            raise ValueError("Start month must be before end month")

        months: List[str] = []
        current = start_date
        while current <= end_date:
            months.append(current.strftime("%Y-%m"))
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        return months

    def get_forecasts(self, query: ForecastQuery) -> List[GridCellForecast]:
        """Get forecasts based on query parameters."""
        months_filter = query.months

        if query.month_range:
            range_months = self.parse_month_range(query.month_range)
            if months_filter:
                months_filter = list(set(months_filter) | set(range_months))
            else:
                months_filter = range_months

        metrics_filter = None
        if query.metrics:
            metrics_filter = [
                MetricName(metric) if not isinstance(metric, MetricName) else metric
                for metric in query.metrics
            ]

        try:
            metric_constraints = query.parse_metric_filters()
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        forecasts = self.repository.get_forecasts(
            country=query.country,
            grid_ids=query.grid_ids,
            months=months_filter,
            metrics=metrics_filter,
            metric_constraints=metric_constraints,
        )

        logger.info("Retrieved %d forecasts", len(forecasts))
        return forecasts

    def get_forecast_summary(self, forecasts: List[GridCellForecast]) -> Dict[str, Any]:
        """Generate summary statistics for forecasts."""
        if not forecasts:
            return {
                "count": 0,
                "countries": [],
                "months": [],
                "grid_cells": 0,
                "metrics_summary": {"avg_map": 0.0, "min_map": None, "max_map": None},
            }

        countries = set()
        months = set()
        grid_cells = set()

        total_map = 0.0
        min_map = float("inf")
        max_map = float("-inf")

        for forecast in forecasts:
            countries.add(forecast.country_id)
            months.add(forecast.month)
            grid_cells.add(forecast.grid_id)

            if hasattr(forecast.metrics, "map"):
                total_map += forecast.metrics.map
                min_map = min(min_map, forecast.metrics.map)
                max_map = max(max_map, forecast.metrics.map)

        avg_map = total_map / len(forecasts) if forecasts else 0.0

        return {
            "count": len(forecasts),
            "countries": sorted(countries),
            "months": sorted(months),
            "grid_cells": len(grid_cells),
            "metrics_summary": {
                "avg_map": round(avg_map, 2),
                "min_map": round(min_map, 2) if min_map != float("inf") else 0,
                "max_map": round(max_map, 2) if max_map != float("-inf") else 0,
            },
        }

    def filter_metrics(
        self, forecast: GridCellForecast, metrics: List[MetricName]
    ) -> Dict[str, Any]:
        """Filter forecast to include only requested metrics."""
        result = {
            "grid_id": forecast.grid_id,
            "latitude": forecast.latitude,
            "longitude": forecast.longitude,
            "country_id": forecast.country_id,
            "month": forecast.month,
        }

        if forecast.admin_1_id:
            result["admin_1_id"] = forecast.admin_1_id
        if forecast.admin_2_id:
            result["admin_2_id"] = forecast.admin_2_id

        metrics_dict = forecast.metrics.model_dump()
        allowed = {metric.value if isinstance(metric, MetricName) else metric for metric in metrics}
        result["metrics"] = {name: value for name, value in metrics_dict.items() if name in allowed}

        return result


__all__ = ["ForecastService"]
