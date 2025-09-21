"""Dependency wiring for FastAPI routes."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from app.domain.repositories import ForecastRepository
from app.services.data_loader import DataLoader
from app.services.forecast_service import ForecastService


@lru_cache
def get_forecast_repository() -> ForecastRepository:
    """Return the configured forecast repository (cached per process)."""
    return DataLoader()


def get_forecast_service(
    repository: ForecastRepository = Depends(get_forecast_repository),
) -> ForecastService:
    """Return the forecast service wired with the repository."""
    return ForecastService(repository=repository)


__all__ = ["get_forecast_repository", "get_forecast_service"]
