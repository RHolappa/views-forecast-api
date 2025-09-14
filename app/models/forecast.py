from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import date


class ForecastMetrics(BaseModel):
    map: float = Field(..., description="Most Accurate Prediction value", ge=0)
    ci_50_low: float = Field(..., description="50% confidence interval lower bound", ge=0)
    ci_50_high: float = Field(..., description="50% confidence interval upper bound", ge=0)
    ci_90_low: float = Field(..., description="90% confidence interval lower bound", ge=0)
    ci_90_high: float = Field(..., description="90% confidence interval upper bound", ge=0)
    ci_99_low: float = Field(..., description="99% confidence interval lower bound", ge=0)
    ci_99_high: float = Field(..., description="99% confidence interval upper bound", ge=0)
    prob_0: float = Field(..., description="Probability of 0 fatalities", ge=0, le=1)
    prob_1: float = Field(..., description="Probability of 1+ fatalities", ge=0, le=1)
    prob_10: float = Field(..., description="Probability of 10+ fatalities", ge=0, le=1)
    prob_100: float = Field(..., description="Probability of 100+ fatalities", ge=0, le=1)
    prob_1000: float = Field(..., description="Probability of 1000+ fatalities", ge=0, le=1)
    prob_10000: float = Field(..., description="Probability of 10000+ fatalities", ge=0, le=1)

    @field_validator('ci_50_high', 'ci_90_high', 'ci_99_high')
    @classmethod
    def validate_ci_high(cls, v, info):
        if 'ci_50_low' in info.data and info.field_name == 'ci_50_high':
            if v < info.data['ci_50_low']:
                raise ValueError('ci_50_high must be >= ci_50_low')
        elif 'ci_90_low' in info.data and info.field_name == 'ci_90_high':
            if v < info.data['ci_90_low']:
                raise ValueError('ci_90_high must be >= ci_90_low')
        elif 'ci_99_low' in info.data and info.field_name == 'ci_99_high':
            if v < info.data['ci_99_low']:
                raise ValueError('ci_99_high must be >= ci_99_low')
        return v


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
    country: Optional[str] = Field(None, description="Filter by country code (ISO 3166-1 alpha-3)")
    grid_ids: Optional[List[int]] = Field(None, description="Filter by specific grid cell IDs")
    months: Optional[List[str]] = Field(None, description="Filter by months (YYYY-MM format)")
    month_range: Optional[str] = Field(None, description="Month range in format YYYY-MM:YYYY-MM")
    metrics: Optional[List[str]] = Field(
        None, 
        description="Specific metrics to return (if not specified, returns all)"
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
    def validate_metrics(cls, v):
        valid_metrics = {
            'map', 'ci_50_low', 'ci_50_high', 'ci_90_low', 'ci_90_high',
            'ci_99_low', 'ci_99_high', 'prob_0', 'prob_1', 'prob_10',
            'prob_100', 'prob_1000', 'prob_10000'
        }
        if v:
            invalid = set(v) - valid_metrics
            if invalid:
                raise ValueError(f"Invalid metrics: {invalid}")
        return v


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