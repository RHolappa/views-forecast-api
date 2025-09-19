import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import verify_api_key
from app.models.forecast import ForecastQuery, MetricName
from app.models.responses import ForecastResponse
from app.services.forecast_service import forecast_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.get("", response_model=ForecastResponse)
async def get_forecasts(
    country: str | None = Query(None, description="Filter by country code (ISO 3166-1 alpha-3)"),
    grid_ids: list[int] | None = Query(None, description="Filter by grid cell IDs"),
    months: list[str] | None = Query(None, description="Filter by months (YYYY-MM format)"),
    month_range: str | None = Query(None, description="Month range (YYYY-MM:YYYY-MM)"),
    metrics: list[MetricName] | None = Query(
        None,
        description="Specific metrics to return (defaults to all metrics)",
    ),
    format: str = Query("json", description="Response format: json or ndjson"),
    _: bool = Depends(verify_api_key),
):
    """
    Retrieve conflict forecasts with optional filtering.

    ## Query Parameters

    - **country**: ISO 3166-1 alpha-3 country code (e.g., "UGA", "KEN")
    - **grid_ids**: List of grid cell IDs (can be repeated: ?grid_ids=1&grid_ids=2)
    - **months**: List of specific months (can be repeated: ?months=2024-01&months=2024-02)
    - **month_range**: Range of months (e.g., "2024-01:2024-06")
    - **metrics**: Specific metrics to include (if not specified, returns all 13 metrics)
    - **format**: Response format ("json" or "ndjson" for streaming)

    ## Available Metrics

    - map: Most Accurate Prediction
    - ci_50_low, ci_50_high: 50% confidence interval
    - ci_90_low, ci_90_high: 90% confidence interval
    - ci_99_low, ci_99_high: 99% confidence interval
    - prob_0: Probability of 0 fatalities
    - prob_1: Probability of 1+ fatalities
    - prob_10: Probability of 10+ fatalities
    - prob_100: Probability of 100+ fatalities
    - prob_1000: Probability of 1000+ fatalities
    - prob_10000: Probability of 10000+ fatalities

    ## Examples

    Get all forecasts for Uganda in January 2024:
    ```
    GET /api/v1/forecasts?country=UGA&months=2024-01
    ```

    Get specific metrics for a grid cell range over 6 months:
    ```
    GET /api/v1/forecasts?grid_ids=1&grid_ids=2&month_range=2024-01:2024-06&metrics=map&metrics=ci_90_low&metrics=ci_90_high
    ```
    """
    try:
        query = ForecastQuery(
            country=country,
            grid_ids=grid_ids,
            months=months,
            month_range=month_range,
            metrics=metrics,
            format=format,
        )

        forecasts = forecast_service.get_forecasts(query)

        if format == "ndjson":
            # Stream as NDJSON for large datasets
            def generate():
                for forecast in forecasts:
                    yield json.dumps(forecast.model_dump()) + "\n"

            return StreamingResponse(
                generate(),
                media_type="application/x-ndjson",
                headers={"X-Total-Count": str(len(forecasts))},
            )
        else:
            # Return standard JSON response
            return ForecastResponse(
                data=forecasts, count=len(forecasts), query=query.model_dump(exclude_none=True)
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error retrieving forecasts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/summary")
async def get_forecast_summary(
    country: str | None = Query(None, description="Filter by country code"),
    grid_ids: list[int] | None = Query(None, description="Filter by grid cell IDs"),
    months: list[str] | None = Query(None, description="Filter by months"),
    month_range: str | None = Query(None, description="Month range"),
    _: bool = Depends(verify_api_key),
):
    """
    Get summary statistics for forecasts matching the query.

    Returns aggregate information including:
    - Total count of forecasts
    - List of countries covered
    - List of months covered
    - Number of unique grid cells
    - Summary statistics for MAP values
    """
    try:
        query = ForecastQuery(
            country=country, grid_ids=grid_ids, months=months, month_range=month_range
        )

        forecasts = forecast_service.get_forecasts(query)
        summary = forecast_service.get_forecast_summary(forecasts)

        return summary

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
