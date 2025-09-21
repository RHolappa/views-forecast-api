import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import verify_api_key
from app.di import get_forecast_repository
from app.domain.repositories import ForecastRepository
from app.models.forecast import GridCellMetadata, MonthMetadata
from app.models.responses import GridCellsResponse, MonthsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/months", response_model=MonthsResponse)
async def get_available_months(
    _: bool = Depends(verify_api_key),
    repository: ForecastRepository = Depends(get_forecast_repository),
):
    """Get list of available forecast months."""
    try:
        months_data = repository.get_available_months()

        months = [
            MonthMetadata(
                month=m["month"], forecast_count=m["forecast_count"], countries=m["countries"]
            )
            for m in months_data
        ]

        return MonthsResponse(data=months, count=len(months))

    except Exception as e:  # pragma: no cover - defensive guard
        logger.error("Error retrieving months: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/grid-cells", response_model=GridCellsResponse)
async def get_grid_cells(
    country: Optional[str] = Query(
        None, description="Filter by country code (UN M49 numeric, zero-padded to 3 digits)"
    ),
    _: bool = Depends(verify_api_key),
    repository: ForecastRepository = Depends(get_forecast_repository),
):
    """Get list of available grid cells."""
    try:
        cells_data = repository.get_grid_cells(country=country)

        cells = [
            GridCellMetadata(
                grid_id=c["grid_id"],
                latitude=c["latitude"],
                longitude=c["longitude"],
                country_id=c["country_id"],
                admin_1_id=c.get("admin_1_id"),
                admin_2_id=c.get("admin_2_id"),
            )
            for c in cells_data
        ]

        countries = list({c.country_id for c in cells}) if cells else []

        return GridCellsResponse(
            data=cells, count=len(cells), countries=sorted(countries) if not country else None
        )

    except Exception as e:  # pragma: no cover - defensive guard
        logger.error("Error retrieving grid cells: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/countries")
async def get_countries(
    _: bool = Depends(verify_api_key),
    repository: ForecastRepository = Depends(get_forecast_repository),
):
    """Get list of available countries."""
    try:
        cells_data = repository.get_grid_cells()
        countries = list({c["country_id"] for c in cells_data})

        return {"countries": sorted(countries), "count": len(countries)}

    except Exception as e:  # pragma: no cover - defensive guard
        logger.error("Error retrieving countries: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
