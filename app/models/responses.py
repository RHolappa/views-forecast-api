from typing import Any

from pydantic import BaseModel, Field

from .forecast import GridCellForecast, GridCellMetadata, MonthMetadata


class ForecastResponse(BaseModel):
    data: list[GridCellForecast]
    count: int = Field(..., description="Total number of forecasts returned")
    query: dict[str, Any] = Field(..., description="Query parameters used")


class GridCellsResponse(BaseModel):
    data: list[GridCellMetadata]
    count: int
    countries: list[str] | None = None


class MonthsResponse(BaseModel):
    data: list[MonthMetadata]
    count: int


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    environment: str


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    status_code: int
