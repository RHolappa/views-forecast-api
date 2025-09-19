import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import verify_api_key
from app.models.forecast import GridCellMetadata, MonthMetadata
from app.models.responses import GridCellsResponse, MonthsResponse
from app.services.data_loader import data_loader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/months", response_model=MonthsResponse)
async def get_available_months(
    _: bool = Depends(verify_api_key)
):
    """
    Get list of available forecast months.

    Returns all months for which forecast data is available,
    along with the count of forecasts and countries covered
    for each month.
    """
    try:
        months_data = data_loader.get_available_months()

        months = [
            MonthMetadata(
                month=m['month'],
                forecast_count=m['forecast_count'],
                countries=m['countries']
            )
            for m in months_data
        ]

        return MonthsResponse(
            data=months,
            count=len(months)
        )

    except Exception as e:
        logger.error(f"Error retrieving months: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/grid-cells", response_model=GridCellsResponse)
async def get_grid_cells(
    country: str | None = Query(None, description="Filter by country code (ISO 3166-1 alpha-3)"),
    _: bool = Depends(verify_api_key)
):
    """
    Get list of available grid cells.

    Returns all grid cells in the system, optionally filtered by country.
    Each grid cell includes its ID, coordinates, and administrative boundaries.
    """
    try:
        cells_data = data_loader.get_grid_cells(country=country)

        cells = [
            GridCellMetadata(
                grid_id=c['grid_id'],
                latitude=c['latitude'],
                longitude=c['longitude'],
                country_id=c['country_id'],
                admin_1_id=c.get('admin_1_id'),
                admin_2_id=c.get('admin_2_id')
            )
            for c in cells_data
        ]

        # Get unique countries
        countries = list({c.country_id for c in cells}) if cells else []

        return GridCellsResponse(
            data=cells,
            count=len(cells),
            countries=sorted(countries) if not country else None
        )

    except Exception as e:
        logger.error(f"Error retrieving grid cells: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/countries")
async def get_countries(
    _: bool = Depends(verify_api_key)
):
    """
    Get list of available countries.

    Returns all country codes that have forecast data available.
    """
    try:
        cells_data = data_loader.get_grid_cells()
        countries = list({c['country_id'] for c in cells_data})

        return {
            "countries": sorted(countries),
            "count": len(countries)
        }

    except Exception as e:
        logger.error(f"Error retrieving countries: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
