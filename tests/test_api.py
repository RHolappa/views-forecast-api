import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


def test_ready_check():
    """Test readiness check endpoint"""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "endpoints" in data


def test_get_forecasts():
    """Test getting forecasts"""
    response = client.get("/api/v1/forecasts")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "count" in data
    assert "query" in data


def test_get_forecasts_with_country_filter():
    """Test getting forecasts with country filter"""
    response = client.get("/api/v1/forecasts?country=UGA")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    if data["count"] > 0:
        # Check that all forecasts are from Uganda
        for forecast in data["data"]:
            assert forecast["country_id"] == "UGA"


def test_get_forecasts_with_month_filter():
    """Test getting forecasts with month filter"""
    response = client.get("/api/v1/forecasts?months=2024-01&months=2024-02")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    if data["count"] > 0:
        # Check that all forecasts are from specified months
        for forecast in data["data"]:
            assert forecast["month"] in ["2024-01", "2024-02"]


def test_get_forecasts_with_month_range():
    """Test getting forecasts with month range"""
    response = client.get("/api/v1/forecasts?month_range=2024-01:2024-03")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


def test_get_forecasts_with_metrics_filter():
    """Test getting forecasts with specific metrics"""
    response = client.get("/api/v1/forecasts?metrics=map&metrics=ci_90_low&metrics=ci_90_high")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


def test_get_forecast_summary():
    """Test forecast summary endpoint"""
    response = client.get("/api/v1/forecasts/summary")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "countries" in data
    assert "months" in data
    assert "grid_cells" in data


def test_get_available_months():
    """Test getting available months"""
    response = client.get("/api/v1/metadata/months")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "count" in data
    if data["count"] > 0:
        month = data["data"][0]
        assert "month" in month
        assert "forecast_count" in month
        assert "countries" in month


def test_get_grid_cells():
    """Test getting grid cells"""
    response = client.get("/api/v1/metadata/grid-cells")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "count" in data
    if data["count"] > 0:
        cell = data["data"][0]
        assert "grid_id" in cell
        assert "latitude" in cell
        assert "longitude" in cell
        assert "country_id" in cell


def test_get_grid_cells_with_country_filter():
    """Test getting grid cells with country filter"""
    response = client.get("/api/v1/metadata/grid-cells?country=UGA")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    if data["count"] > 0:
        # Check that all cells are from Uganda
        for cell in data["data"]:
            assert cell["country_id"] == "UGA"


def test_get_countries():
    """Test getting available countries"""
    response = client.get("/api/v1/metadata/countries")
    assert response.status_code == 200
    data = response.json()
    assert "countries" in data
    assert "count" in data
    assert isinstance(data["countries"], list)


def test_invalid_country_code():
    """Test validation of invalid country code"""
    response = client.get("/api/v1/forecasts?country=US")  # Too short
    assert response.status_code == 400


def test_invalid_month_format():
    """Test validation of invalid month format"""
    response = client.get("/api/v1/forecasts?months=2024-13")  # Invalid month
    assert response.status_code == 400


def test_invalid_month_range():
    """Test validation of invalid month range"""
    response = client.get("/api/v1/forecasts?month_range=2024-01-2024-06")  # Wrong separator
    assert response.status_code == 400


def test_invalid_metrics():
    """Test validation of invalid metrics"""
    response = client.get("/api/v1/forecasts?metrics=invalid_metric")
    assert response.status_code == 400