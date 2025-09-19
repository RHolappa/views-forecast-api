from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import date


class MetricName(str, Enum):
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
    ci_50_low: Optional[float] = Field(None, description="50% confidence interval lower bound", ge=0)
    ci_50_high: Optional[float] = Field(None, description="50% confidence interval upper bound", ge=0)
    ci_90_low: Optional[float] = Field(None, description="90% confidence interval lower bound", ge=0)
    ci_90_high: Optional[float] = Field(None, description="90% confidence interval upper bound", ge=0)
    ci_99_low: Optional[float] = Field(None, description="99% confidence interval lower bound", ge=0)
    ci_99_high: Optional[float] = Field(None, description="99% confidence interval upper bound", ge=0)
    prob_0: Optional[float] = Field(None, description="Probability of 0 fatalities", ge=0, le=1)
    prob_1: Optional[float] = Field(None, description="Probability of 1+ fatalities", ge=0, le=1)
    prob_10: Optional[float] = Field(None, description="Probability of 10+ fatalities", ge=0, le=1)
    prob_100: Optional[float] = Field(None, description="Probability of 100+ fatalities", ge=0, le=1)
    prob_1000: Optional[float] = Field(None, description="Probability of 1000+ fatalities", ge=0, le=1)
    prob_10000: Optional[float] = Field(None, description="Probability of 10000+ fatalities", ge=0, le=1)

    @field_validator('ci_50_high', 'ci_90_high', 'ci_99_high')
    @classmethod
    def validate_ci_high(cls, v, info):
        if v is None:
            return v

        low_field = {
            'ci_50_high': 'ci_50_low',
            'ci_90_high': 'ci_90_low',
            'ci_99_high': 'ci_99_low'
        }[info.field_name]
        low_value = info.data.get(low_field)
        if low_value is not None and v < low_value:
            raise ValueError(f"{info.field_name} must be >= {low_field}")
        return v

    @model_validator(mode="after")
    def ensure_metrics_present(cls, values):  # type: ignore[override]
        if not any(value is not None for value in values.__dict__.values()):
            raise ValueError("At least one metric value must be provided")
        return values

    def model_dump(self, *args, **kwargs):  # type: ignore[override]
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


class GridCellForecast(BaseModel):
    grid_id: int = Field(..., description="Unique grid cell identifier")
    latitude: float = Field(..., ge=-90, le=90, description="Grid cell center latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Grid cell center longitude")
    country_id: str = Field(..., description="ISO 3166-1 alpha-3 country code")
    admin_1_id: Optional[str] = Field(None, description="Admin level 1 identifier")
    admin_2_id: Optional[str] = Field(None, description="Admin level 2 identifier")
    month: str = Field(..., description="Forecast month in YYYY-MM format")
    metrics: ForecastMetrics


class ForecastQuery(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    country: Optional[str] = Field(None, description="Filter by country code (ISO 3166-1 alpha-3)")
    grid_ids: Optional[List[int]] = Field(None, description="Filter by specific grid cell IDs")
    months: Optional[List[str]] = Field(None, description="Filter by months (YYYY-MM format)")
    month_range: Optional[str] = Field(None, description="Month range in format YYYY-MM:YYYY-MM")
    metrics: Optional[List[MetricName]] = Field(
        None,
        description="Specific metrics to return (if not specified, returns all)",
        examples=[["map", "ci_90_low", "ci_90_high"]]
    )
    format: str = Field("json", description="Response format: json or ndjson")
    
    @field_validator('country')
    @classmethod
    def validate_country(cls, v):
        if v and len(v) != 3:
            raise ValueError('Country code must be ISO 3166-1 alpha-3 (3 characters)')
        return v.upper() if v else v
    
    @field_validator('months')
    @classmethod
    def validate_months(cls, v):
        if v:
            for month in v:
                try:
                    date.fromisoformat(f"{month}-01")
                except ValueError:
                    raise ValueError(f"Invalid month format: {month}. Use YYYY-MM")
        return v
    
    @field_validator('month_range')
    @classmethod
    def validate_month_range(cls, v):
        if v:
            parts = v.split(':')
            if len(parts) != 2:
                raise ValueError("Month range must be in format YYYY-MM:YYYY-MM")
            for part in parts:
                try:
                    date.fromisoformat(f"{part}-01")
                except ValueError:
                    raise ValueError(f"Invalid month format in range: {part}")
        return v
    
    @field_validator('metrics')
    @classmethod
    def deduplicate_metrics(cls, v):
        if not v:
            return v
        unique: List[MetricName] = []
        for metric in v:
            if metric not in unique:
                unique.append(metric)
        return unique


class GridCellMetadata(BaseModel):
    grid_id: int
    latitude: float
    longitude: float
    country_id: str
    admin_1_id: Optional[str] = None
    admin_2_id: Optional[str] = None


class MonthMetadata(BaseModel):
    month: str
    forecast_count: int
    countries: List[str]
