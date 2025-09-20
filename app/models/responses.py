"""Pydantic response models for API endpoints.

This module defines the response models used by the VIEWS Forecast API
endpoints, ensuring consistent response structures across all API operations.
All models use Pydantic for validation and JSON serialization.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .forecast import GridCellForecast, GridCellMetadata, MonthMetadata


class ForecastResponse(BaseModel):
    """API response containing forecast data.

    Standard response structure for forecast endpoints, including
    the forecast data, result count, and query parameters used.

    Attributes:
        data: List of grid cell forecasts matching the query.
        count: Total number of forecasts returned.
        query: Original query parameters for reference.
    """

    data: List[GridCellForecast]
    count: int = Field(..., description="Total number of forecasts returned")
    query: Dict[str, Any] = Field(..., description="Query parameters used")


class GridCellsResponse(BaseModel):
    """API response containing grid cell metadata.

    Response structure for grid cell metadata endpoints, providing
    geographic and administrative information without forecast data.

    Attributes:
        data: List of grid cell metadata records.
        count: Total number of grid cells returned.
        countries: Optional list of unique country codes in the response.
    """

    data: List[GridCellMetadata]
    count: int
    countries: Optional[List[str]] = None


class MonthsResponse(BaseModel):
    """API response containing available months metadata.

    Response structure for month availability endpoints, showing
    which months have forecast data available.

    Attributes:
        data: List of month metadata records.
        count: Total number of months with available data.
    """

    data: List[MonthMetadata]
    count: int


class HealthResponse(BaseModel):
    """Health check endpoint response.

    Simple response model for health check endpoints, providing
    basic service status information.

    Attributes:
        status: Service health status (typically 'healthy').
        version: API version number.
        environment: Current deployment environment.
    """

    status: str = "healthy"
    version: str = "1.0.0"
    environment: str


class ErrorResponse(BaseModel):
    """Error response model.

    Standardized error response structure for API error conditions,
    providing consistent error reporting across all endpoints.

    Attributes:
        error: Brief error message.
        detail: Optional detailed error information.
        status_code: HTTP status code of the error.
    """

    error: str
    detail: Optional[str] = None
    status_code: int
