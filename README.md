# VIEWS Conflict Forecast API

A high-performance REST API for serving grid-level conflict predictions with uncertainty quantification. Built with FastAPI and designed for scalability.

## Features

- **Grid-cell level forecasts** with 13 prediction metrics including:
  - Most Accurate Prediction (MAP)
  - Confidence intervals (50%, 90%, 99%)
  - Probability thresholds (0, 1, 10, 100, 1000, 10000 fatalities)
- **Flexible filtering** by country, grid cells, and time periods
- **Multiple response formats** (JSON, NDJSON for streaming)
- **High performance** with caching and efficient data storage
- **Production-ready** with health checks, logging, and Docker support

## Quick Start

### Prerequisites

- Python 3.11+
- pip or conda for package management

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd views-forecast-api
```

2. Install dependencies:
```bash
make install
```

3. Copy and configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the API:
```bash
make dev  # Development mode with auto-reload
# or
make run  # Production mode
```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:
- **Interactive API docs**: http://localhost:8000/docs
- **OpenAPI schema**: http://localhost:8000/openapi.json

(X-API-Key header from env file can be used)

### Key Endpoints

#### Get Forecasts
```bash
GET /api/v1/forecasts
```

Query parameters:
- `country`: ISO 3166-1 alpha-3 country code (e.g., "UGA")
- `grid_ids`: List of grid cell IDs
- `months`: Specific months (YYYY-MM format)
- `month_range`: Range of months (YYYY-MM:YYYY-MM)
- `metrics`: Specific metrics to return
- `format`: Response format (json or ndjson)

Example:
```bash
curl "http://localhost:8000/api/v1/forecasts?country=UGA&months=2024-01&metrics=map&metrics=ci_90_low&metrics=ci_90_high"
```

#### Get Available Months
```bash
GET /api/v1/metadata/months
```

Returns all months with available forecast data.

#### Get Grid Cells
```bash
GET /api/v1/metadata/grid-cells?country=UGA
```

Returns grid cells, optionally filtered by country.

## Data Storage

The API supports two data storage modes:

### Local Data (Development)
- Place Parquet files in `data/sample/` directory
- Set `USE_LOCAL_DATA=true` in `.env`
- Sample data is auto-generated if no files are found

### Cloud Storage (Production)
- Configure cloud credentials in `.env`
- Set `USE_LOCAL_DATA=false`
- Supports AWS S3, Google Cloud Storage, Azure Blob Storage

## Configuration

Key environment variables:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=development

# Data Source
USE_LOCAL_DATA=true
DATA_PATH=data/sample

# Cloud Storage (for production)
CLOUD_BUCKET_NAME=views-forecast-data
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret

# Cache
CACHE_TTL_SECONDS=3600
CACHE_MAX_SIZE=1000

# Optional Authentication
API_KEY=your-api-key
```

## Development

### Running Tests
```bash
make test
```

### Code Quality
```bash
make lint    # Run linting
make format  # Auto-format code
```

### Project Structure
```
views-forecast-api/
├── app/
│   ├── api/          # API routes and dependencies
│   ├── core/         # Configuration and settings
│   ├── models/       # Pydantic models
│   ├── services/     # Business logic
│   └── main.py       # Application entry point
├── tests/            # Test suite
├── data/             # Local data storage
└── requirements.txt  # Dependencies
```

## Docker Deployment

### Build and Run with Docker
```bash
# Build image
make docker-build

# Run container
make docker-run
```

### Using Docker Compose
```bash
docker-compose up -d
```

## Production Deployment

### Health Checks
- `/health` - Basic health check
- `/ready` - Readiness probe for orchestration

### Scaling Considerations

1. **Horizontal Scaling**: The API is stateless and can be scaled horizontally behind a load balancer
2. **Caching**: Configure cache size based on available memory
3. **Data Storage**: Use cloud storage (S3/GCS) for production data
4. **Monitoring**: Integrate with APM tools using OpenTelemetry

### Security

- Use API keys in production (`API_KEY` environment variable)
- Configure CORS origins appropriately
- Use HTTPS in production (terminate TLS at load balancer)
- Regularly update dependencies

## API Response Examples

### Forecast Response
```json
{
  "data": [
    {
      "grid_id": 1,
      "latitude": 0.5,
      "longitude": 32.5,
      "country_id": "UGA",
      "month": "2024-01",
      "metrics": {
        "map": 10.5,
        "ci_90_low": 4.0,
        "ci_90_high": 20.0
      }
    }
  ],
  "count": 1,
  "query": {
    "country": "UGA",
    "months": ["2024-01"],
    "metrics": ["map", "ci_90_low", "ci_90_high"]
  }
}
```

### NDJSON Streaming Format
```json
{"grid_id":1,"latitude":0.5,"longitude":32.5,"country_id":"UGA","month":"2024-01","metrics":{...}}
{"grid_id":2,"latitude":1.5,"longitude":33.5,"country_id":"UGA","month":"2024-01","metrics":{...}}
```

## Future Enhancements

The API is designed to easily support:
- Aggregation endpoints for regional summaries
- Administrative boundary queries
- Time series analysis endpoints
- Webhook notifications for new data
- GraphQL interface
- Real-time WebSocket updates

## License

[Your License Here]

## Support

For issues and questions, please open an issue in the repository.