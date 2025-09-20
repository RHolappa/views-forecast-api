import pytest

from app.core.config import settings
from app.models.forecast import ForecastQuery, MetricName
from app.services.data_loader import DataLoader
from app.services.forecast_service import ForecastService


def test_parse_month_range():
    """Test month range parsing"""
    service = ForecastService()

    # Test simple range
    months = service.parse_month_range("2024-01:2024-03")
    assert months == ["2024-01", "2024-02", "2024-03"]

    # Test year boundary
    months = service.parse_month_range("2023-11:2024-02")
    assert months == ["2023-11", "2023-12", "2024-01", "2024-02"]

    # Test single month
    months = service.parse_month_range("2024-06:2024-06")
    assert months == ["2024-06"]

    # Test invalid range (start > end)
    with pytest.raises(ValueError):
        service.parse_month_range("2024-03:2024-01")

    # Test invalid format
    with pytest.raises(ValueError):
        service.parse_month_range("2024-01-2024-03")


def test_get_forecasts():
    """Test getting forecasts"""
    service = ForecastService()

    # Test basic query
    query = ForecastQuery()
    forecasts = service.get_forecasts(query)
    assert isinstance(forecasts, list)

    # Test with country filter
    query = ForecastQuery(country="800")
    forecasts = service.get_forecasts(query)
    for forecast in forecasts:
        assert forecast.country_id == "800"

    # Test with month range
    query = ForecastQuery(month_range="2024-01:2024-02")
    forecasts = service.get_forecasts(query)
    for forecast in forecasts:
        assert forecast.month in ["2024-01", "2024-02"]

    # Test with metric filter
    query = ForecastQuery(metrics=[MetricName.map, MetricName.prob_10])
    forecasts = service.get_forecasts(query)
    for forecast in forecasts:
        assert set(forecast.metrics.model_dump().keys()) == {"map", "prob_10"}


def test_get_forecast_summary():
    """Test forecast summary generation"""
    service = ForecastService()

    # Get some forecasts
    query = ForecastQuery()
    forecasts = service.get_forecasts(query)

    # Generate summary
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


def test_data_loader_falls_back_when_credentials_missing(monkeypatch, tmp_path):
    """Cloud backend should fall back to sample data if AWS credentials are blank."""

    monkeypatch.setattr(settings, "data_backend", "cloud", raising=False)
    monkeypatch.setattr(settings, "use_local_data", False, raising=False)
    monkeypatch.setattr(settings, "aws_access_key_id", "", raising=False)
    monkeypatch.setattr(settings, "aws_secret_access_key", "", raising=False)
    monkeypatch.setattr(settings, "data_path", str(tmp_path), raising=False)

    loader = DataLoader()

    assert loader.backend == "parquet"
    assert (tmp_path / "sample_data.parquet").exists()
    assert loader.get_forecasts(), "Sample data should provide forecast rows"


def test_data_loader_falls_back_when_use_local_data(monkeypatch, tmp_path):
    """USE_LOCAL_DATA=true should force sample data usage even for cloud backend."""

    monkeypatch.setattr(settings, "data_backend", "cloud", raising=False)
    monkeypatch.setattr(settings, "use_local_data", True, raising=False)
    monkeypatch.setattr(settings, "aws_access_key_id", "key", raising=False)
    monkeypatch.setattr(settings, "aws_secret_access_key", "secret", raising=False)
    monkeypatch.setattr(settings, "data_path", str(tmp_path), raising=False)

    loader = DataLoader()

    assert loader.backend == "parquet"
    assert (tmp_path / "sample_data.parquet").exists()
    assert loader.get_forecasts(), "Sample data should provide forecast rows"
