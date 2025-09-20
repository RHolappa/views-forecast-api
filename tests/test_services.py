import pytest

from app.models.forecast import ForecastQuery, MetricName
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
