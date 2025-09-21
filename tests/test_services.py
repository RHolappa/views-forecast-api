import pytest

from app.core.config import settings
from app.models.forecast import ForecastQuery, MetricName
from app.services.data_loader import ParquetForecastRepository
from app.services.forecast_service import ForecastService


@pytest.fixture()
def repository(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_path", str(tmp_path), raising=False)
    return ParquetForecastRepository()


@pytest.fixture()
def service(repository):
    return ForecastService(repository)


def test_parse_month_range(service):
    """Test month range parsing."""

    months = service.parse_month_range("2024-01:2024-03")
    assert months == ["2024-01", "2024-02", "2024-03"]

    months = service.parse_month_range("2023-11:2024-02")
    assert months == ["2023-11", "2023-12", "2024-01", "2024-02"]

    months = service.parse_month_range("2024-06:2024-06")
    assert months == ["2024-06"]

    with pytest.raises(ValueError):
        service.parse_month_range("2024-03:2024-01")

    with pytest.raises(ValueError):
        service.parse_month_range("2024-01-2024-03")


def test_get_forecasts(service):
    """Test getting forecasts."""
    forecasts = service.get_forecasts(ForecastQuery())
    assert isinstance(forecasts, list)

    query = ForecastQuery(country="800")
    forecasts = service.get_forecasts(query)
    for forecast in forecasts:
        assert forecast.country_id == "800"

    query = ForecastQuery(month_range="2024-01:2024-02")
    forecasts = service.get_forecasts(query)
    for forecast in forecasts:
        assert forecast.month in ["2024-01", "2024-02"]

    query = ForecastQuery(metrics=[MetricName.map, MetricName.prob_10])
    forecasts = service.get_forecasts(query)
    for forecast in forecasts:
        assert set(forecast.metrics.model_dump().keys()) == {"map", "prob_10"}


def test_get_forecast_summary(service):
    """Test forecast summary generation."""
    forecasts = service.get_forecasts(ForecastQuery())
    summary = service.get_forecast_summary(forecasts)

    assert "count" in summary
    assert "countries" in summary
    assert "months" in summary
    assert "grid_cells" in summary
    assert "metrics_summary" in summary

    if forecasts:
        assert summary["count"] == len(forecasts)
        assert len(summary["countries"]) > 0
        assert len(summary["months"]) > 0
        assert summary["grid_cells"] > 0


def test_repository_generates_sample_data(monkeypatch, tmp_path):
    """Repository should generate sample data when none exists."""
    monkeypatch.setattr(settings, "data_path", str(tmp_path), raising=False)

    repository = ParquetForecastRepository()
    forecasts = repository.get_forecasts()

    assert forecasts, "Sample data should provide forecast rows"
    assert (tmp_path / "sample_data.parquet").exists()
