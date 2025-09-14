from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .forecast import GridCellForecast, GridCellMetadata, MonthMetadata


class ForecastResponse(BaseModel):
    data: List[GridCellForecast]
    count: int = Field(..., description="Total number of forecasts returned")
    query: Dict[str, Any] = Field(..., description="Query parameters used")


class GridCellsResponse(BaseModel):
    data: List[GridCellMetadata]
    count: int
    countries: Optional[List[str]] = None


class MonthsResponse(BaseModel):
    data: List[MonthMetadata]
    count: int


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    environment: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int