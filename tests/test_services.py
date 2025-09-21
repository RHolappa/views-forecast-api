import pandas as pd
import pytest

from app.core.config import settings
from app.models.forecast import ForecastQuery, MetricName
from app.services.data_loader import DataLoader
from app.services.forecast_service import ForecastService
from app.services.sample_data import FORECAST_COLUMNS


@pytest.fixture()
def repository(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_path", str(tmp_path), raising=False)
    data = [
        {
            "grid_id": 1,
            "latitude": 11.1,
            "longitude": 14.4,
            "country_id": "074",
            "admin_1_id": "074-ADM1-00",
            "admin_2_id": "074-ADM2-00",
            "month": "2024-01",
            "map": 60.0,
            "ci_50_low": 45.0,
            "ci_50_high": 75.0,
            "ci_90_low": 30.0,
            "ci_90_high": 90.0,
            "ci_99_low": 25.0,
            "ci_99_high": 105.0,
            "prob_0": 0.1,
            "prob_1": 0.9,
            "prob_10": 0.5,
            "prob_100": 0.2,
            "prob_1000": 0.15,
            "prob_10000": 0.05,
        },
        {
            "grid_id": 1,
            "latitude": 11.1,
            "longitude": 14.4,
            "country_id": "074",
            "admin_1_id": "074-ADM1-00",
            "admin_2_id": "074-ADM2-00",
            "month": "2024-02",
            "map": 40.0,
            "ci_50_low": 30.0,
            "ci_50_high": 50.0,
            "ci_90_low": 20.0,
            "ci_90_high": 60.0,
            "ci_99_low": 15.0,
            "ci_99_high": 70.0,
            "prob_0": 0.2,
            "prob_1": 0.8,
            "prob_10": 0.3,
            "prob_100": 0.1,
            "prob_1000": 0.05,
            "prob_10000": 0.01,
        },
        {
            "grid_id": 2,
            "latitude": -1.2,
            "longitude": 32.5,
            "country_id": "800",
            "admin_1_id": "800-ADM1-00",
            "admin_2_id": "800-ADM2-00",
            "month": "2024-01",
            "map": 15.0,
            "ci_50_low": 10.0,
            "ci_50_high": 20.0,
            "ci_90_low": 5.0,
            "ci_90_high": 25.0,
            "ci_99_low": 2.0,
            "ci_99_high": 30.0,
            "prob_0": 0.4,
            "prob_1": 0.6,
            "prob_10": 0.2,
            "prob_100": 0.05,
            "prob_1000": 0.01,
            "prob_10000": 0.0,
        },
    ]

    df = pd.DataFrame(data, columns=FORECAST_COLUMNS)
    parquet_path = tmp_path / "forecasts.parquet"
    df.to_parquet(parquet_path, index=False)

    return DataLoader(data_path=str(tmp_path), backend="parquet")


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

    repository = DataLoader(data_path=str(tmp_path), backend="parquet")
    forecasts = repository.get_forecasts()

    assert forecasts, "Sample data should provide forecast rows"
    assert (tmp_path / "sample_data.parquet").exists()


def test_metric_filters(service):
    query = ForecastQuery(metric_filters=["map>50"], metrics=[MetricName.map])
    forecasts = service.get_forecasts(query)
    assert len(forecasts) == 1
    assert forecasts[0].metrics.map > 50

    query = ForecastQuery(metric_filters=["prob_1000>=0.1"])
    forecasts = service.get_forecasts(query)
    assert {f.grid_id for f in forecasts} == {1}

    with pytest.raises(ValueError):
        service.get_forecasts(ForecastQuery(metric_filters=["map>>50"]))
