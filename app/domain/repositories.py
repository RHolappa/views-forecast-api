"""Domain-level repository protocols."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from app.models.forecast import GridCellForecast, MetricConstraint, MetricName


class ForecastRepository(Protocol):
    """Abstraction for retrieving forecast data.

    Concrete implementations may load data from parquet files,
    databases, or remote services. Application services should
    depend on this protocol instead of concrete data loaders.
    """

    def get_forecasts(
        self,
        country: Optional[str] = None,
        grid_ids: Optional[List[int]] = None,
        months: Optional[List[str]] = None,
        metrics: Optional[List[MetricName]] = None,
        metric_constraints: Optional[List[MetricConstraint]] = None,
    ) -> List[GridCellForecast]:
        """Return forecasts filtered by the provided criteria."""

    def get_available_months(self) -> List[Dict[str, Any]]:
        """Return summary metadata for available forecast months."""

    def get_grid_cells(self, country: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return metadata for unique grid cells, optionally filtered by country."""
