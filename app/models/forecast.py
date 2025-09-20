"""Pydantic models for forecast data and API queries.

This module defines the data models used throughout the VIEWS Forecast API,
including forecast metrics, grid cell data, query parameters, and metadata
structures. All models use Pydantic for validation and serialization.
"""

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MetricName(str, Enum):
    """Enumeration of available forecast metric types.

    Defines all supported metrics for conflict forecasts, including
    point estimates (MAP), confidence intervals, and exceedance probabilities.
    """

    map = "map"
    ci_50_low = "ci_50_low"
    ci_50_high = "ci_50_high"
    ci_90_low = "ci_90_low"
    ci_90_high = "ci_90_high"
    ci_99_low = "ci_99_low"
    ci_99_high = "ci_99_high"
    prob_0 = "prob_0"
    prob_1 = "prob_1"
    prob_10 = "prob_10"
    prob_100 = "prob_100"
    prob_1000 = "prob_1000"
    prob_10000 = "prob_10000"


ALL_METRIC_NAMES = tuple(metric.value for metric in MetricName)


class ForecastMetrics(BaseModel):
    """Complete or filtered set of available forecast metrics."""

    model_config = ConfigDict(extra="forbid")

    map: Optional[float] = Field(None, description="Most Accurate Prediction value", ge=0)
    ci_50_low: Optional[float] = Field(
        None, description="50% confidence interval lower bound", ge=0
    )
    ci_50_high: Optional[float] = Field(
        None, description="50% confidence interval upper bound", ge=0
    )
    ci_90_low: Optional[float] = Field(
        None, description="90% confidence interval lower bound", ge=0
    )
    ci_90_high: Optional[float] = Field(
        None, description="90% confidence interval upper bound", ge=0
    )
    ci_99_low: Optional[float] = Field(
        None, description="99% confidence interval lower bound", ge=0
    )
    ci_99_high: Optional[float] = Field(
        None, description="99% confidence interval upper bound", ge=0
    )
    prob_0: Optional[float] = Field(None, description="Probability of 0 fatalities", ge=0, le=1)
    prob_1: Optional[float] = Field(None, description="Probability of 1+ fatalities", ge=0, le=1)
    prob_10: Optional[float] = Field(None, description="Probability of 10+ fatalities", ge=0, le=1)
    prob_100: Optional[float] = Field(
        None, description="Probability of 100+ fatalities", ge=0, le=1
    )
    prob_1000: Optional[float] = Field(
        None, description="Probability of 1000+ fatalities", ge=0, le=1
    )
    prob_10000: Optional[float] = Field(
        None, description="Probability of 10000+ fatalities", ge=0, le=1
    )

    @field_validator("ci_50_high", "ci_90_high", "ci_99_high")
    @classmethod
    def validate_ci_high(cls, v, info):
        """Validate that confidence interval upper bounds exceed lower bounds.

        Args:
            v: The upper bound value to validate.
            info: Validation context containing field name and other data.

        Returns:
            The validated upper bound value.

        Raises:
            ValueError: If upper bound is less than corresponding lower bound.
        """
        if v is None:
            return v

        low_field = {
            "ci_50_high": "ci_50_low",
            "ci_90_high": "ci_90_low",
            "ci_99_high": "ci_99_low",
        }[info.field_name]
        low_value = info.data.get(low_field)
        if low_value is not None and v < low_value:
            raise ValueError(f"{info.field_name} must be >= {low_field}")
        return v

    @model_validator(mode="after")
    def ensure_metrics_present(cls, values):  # type: ignore[override]
        """Ensure at least one metric value is provided.

        Args:
            values: The model instance to validate.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If no metric values are provided.
        """
        if not any(value is not None for value in values.__dict__.values()):
            raise ValueError("At least one metric value must be provided")
        return values

    def model_dump(self, *args, **kwargs):  # type: ignore[override]
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


class GridCellForecast(BaseModel):
    """Model representing a single grid cell forecast.

    Contains geographic identifiers, temporal information, and forecast
    metrics for a specific grid cell in a given month.

    Attributes:
        grid_id: Unique identifier for the grid cell.
        latitude: Center latitude of the grid cell.
        longitude: Center longitude of the grid cell.
        country_id: UN M49 numeric country code.
        admin_1_id: First-level administrative division identifier.
        admin_2_id: Second-level administrative division identifier.
        month: Forecast month in YYYY-MM format.
        metrics: Forecast metrics for this grid cell.
    """

    grid_id: int = Field(..., description="Unique grid cell identifier")
    latitude: float = Field(..., ge=-90, le=90, description="Grid cell center latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Grid cell center longitude")
    country_id: str = Field(
        ..., description="UN M49 numeric country code (zero-padded to 3 digits)"
    )
    admin_1_id: Optional[str] = Field(None, description="Admin level 1 identifier")
    admin_2_id: Optional[str] = Field(None, description="Admin level 2 identifier")
    month: str = Field(..., description="Forecast month in YYYY-MM format")
    metrics: ForecastMetrics


class ForecastQuery(BaseModel):
    """Model for forecast API query parameters.

    Validates and parses query parameters for filtering forecast data,
    including geographic, temporal, and metric filters.

    Attributes:
        country: Optional UN M49 country code filter.
        grid_ids: Optional list of specific grid cell IDs.
        months: Optional list of months to query.
        month_range: Optional month range in YYYY-MM:YYYY-MM format.
        metrics: Optional list of specific metrics to return.
        format: Response format (json or ndjson).
    """

    model_config = ConfigDict(use_enum_values=True)

    country: Optional[str] = Field(
        None,
        description="Filter by country code (UN M49 numeric, zero-padded to 3 digits)",
    )
    grid_ids: Optional[List[int]] = Field(None, description="Filter by specific grid cell IDs")
    months: Optional[List[str]] = Field(None, description="Filter by months (YYYY-MM format)")
    month_range: Optional[str] = Field(None, description="Month range in format YYYY-MM:YYYY-MM")
    metrics: Optional[List[MetricName]] = Field(
        None,
        description="Specific metrics to return (if not specified, returns all)",
        examples=[["map", "ci_90_low", "ci_90_high"]],
    )
    format: str = Field("json", description="Response format: json or ndjson")

    @field_validator("country")
    @classmethod
    def validate_country(cls, v):
        """Validate UN M49 country code format.

        Args:
            v: Country code to validate.

        Returns:
            Validated country code.

        Raises:
            ValueError: If country code is not 3-digit numeric.
        """
        if not v:
            return v
        if not v.isdigit() or len(v) != 3:
            raise ValueError("Country code must be a UN M49 numeric identifier padded to 3 digits")
        return v

    @field_validator("months")
    @classmethod
    def validate_months(cls, v):
        """Validate month format (YYYY-MM).

        Args:
            v: List of months to validate.

        Returns:
            Validated list of months.

        Raises:
            ValueError: If any month is not in YYYY-MM format.
        """
        if v:
            for month in v:
                try:
                    date.fromisoformat(f"{month}-01")
                except ValueError as e:
                    raise ValueError(f"Invalid month format: {month}. Use YYYY-MM") from e
        return v

    @field_validator("month_range")
    @classmethod
    def validate_month_range(cls, v):
        """Validate month range format (YYYY-MM:YYYY-MM).

        Args:
            v: Month range string to validate.

        Returns:
            Validated month range.

        Raises:
            ValueError: If range is not in correct format.
        """
        if v:
            parts = v.split(":")
            if len(parts) != 2:
                raise ValueError("Month range must be in format YYYY-MM:YYYY-MM")
            for part in parts:
                try:
                    date.fromisoformat(f"{part}-01")
                except ValueError as e:
                    raise ValueError(f"Invalid month format in range: {part}") from e
        return v

    @field_validator("metrics")
    @classmethod
    def deduplicate_metrics(cls, v):
        """Remove duplicate metrics from list.

        Args:
            v: List of metrics that may contain duplicates.

        Returns:
            List with duplicates removed, preserving order.
        """
        if not v:
            return v
        unique: List[MetricName] = []
        for metric in v:
            if metric not in unique:
                unique.append(metric)
        return unique


class GridCellMetadata(BaseModel):
    """Model for grid cell metadata.

    Contains geographic and administrative information about a grid cell
    without forecast data.

    Attributes:
        grid_id: Unique identifier for the grid cell.
        latitude: Center latitude of the grid cell.
        longitude: Center longitude of the grid cell.
        country_id: UN M49 numeric country code.
        admin_1_id: First-level administrative division.
        admin_2_id: Second-level administrative division.
    """

    grid_id: int
    latitude: float
    longitude: float
    country_id: str
    admin_1_id: Optional[str] = None
    admin_2_id: Optional[str] = None


class MonthMetadata(BaseModel):
    """Model for monthly forecast metadata.

    Provides summary information about available forecasts for a given month.

    Attributes:
        month: Month in YYYY-MM format.
        forecast_count: Number of forecasts available for this month.
        countries: List of country codes with data for this month.
    """

    month: str
    forecast_count: int
    countries: List[str]
