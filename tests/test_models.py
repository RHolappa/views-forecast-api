import pytest
from pydantic import ValidationError
from app.models.forecast import ForecastMetrics, GridCellForecast, ForecastQuery


def test_forecast_metrics_validation():
    """Test ForecastMetrics model validation"""
    # Valid metrics
    metrics = ForecastMetrics(
        map=10.5,
        ci_50_low=7.0,
        ci_50_high=14.0,
        ci_90_low=4.0,
        ci_90_high=20.0,
        ci_99_low=1.0,
        ci_99_high=30.0,
        prob_0=0.1,
        prob_1=0.3,
        prob_10=0.2,
        prob_100=0.1,
        prob_1000=0.05,
        prob_10000=0.01
    )
    assert metrics.map == 10.5
    assert metrics.ci_50_low < metrics.ci_50_high
    
    # Invalid: CI high < CI low
    with pytest.raises(ValidationError):
        ForecastMetrics(
            map=10.5,
            ci_50_low=14.0,
            ci_50_high=7.0,  # Invalid: lower than ci_50_low
            ci_90_low=4.0,
            ci_90_high=20.0,
            ci_99_low=1.0,
            ci_99_high=30.0,
            prob_0=0.1,
            prob_1=0.3,
            prob_10=0.2,
            prob_100=0.1,
            prob_1000=0.05,
            prob_10000=0.01
        )
    
    # Invalid: Probability > 1
    with pytest.raises(ValidationError):
        ForecastMetrics(
            map=10.5,
            ci_50_low=7.0,
            ci_50_high=14.0,
            ci_90_low=4.0,
            ci_90_high=20.0,
            ci_99_low=1.0,
            ci_99_high=30.0,
            prob_0=1.5,  # Invalid: > 1
            prob_1=0.3,
            prob_10=0.2,
            prob_100=0.1,
            prob_1000=0.05,
            prob_10000=0.01
        )


def test_grid_cell_forecast():
    """Test GridCellForecast model"""
    forecast = GridCellForecast(
        grid_id=1,
        latitude=0.5,
        longitude=32.5,
        country_id="UGA",
        month="2024-01",
        metrics=ForecastMetrics(
            map=10.5,
            ci_50_low=7.0,
            ci_50_high=14.0,
            ci_90_low=4.0,
            ci_90_high=20.0,
            ci_99_low=1.0,
            ci_99_high=30.0,
            prob_0=0.1,
            prob_1=0.3,
            prob_10=0.2,
            prob_100=0.1,
            prob_1000=0.05,
            prob_10000=0.01
        )
    )
    assert forecast.grid_id == 1
    assert forecast.country_id == "UGA"
    assert forecast.admin_1_id is None


def test_forecast_query_validation():
    """Test ForecastQuery validation"""
    # Valid query
    query = ForecastQuery(
        country="UGA",
        months=["2024-01", "2024-02"],
        metrics=["map", "ci_90_low", "ci_90_high"]
    )
    assert query.country == "UGA"
    assert len(query.months) == 2
    
    # Test country code validation
    query = ForecastQuery(country="uga")
    assert query.country == "UGA"  # Should be uppercase
    
    # Invalid country code length
    with pytest.raises(ValidationError):
        ForecastQuery(country="US")  # Too short
    
    # Invalid month format
    with pytest.raises(ValidationError):
        ForecastQuery(months=["2024-13"])  # Invalid month
    
    # Invalid month range format
    with pytest.raises(ValidationError):
        ForecastQuery(month_range="2024-01-2024-06")  # Wrong separator
    
    # Invalid metrics
    with pytest.raises(ValidationError):
        ForecastQuery(metrics=["invalid_metric"])