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
git clone https://github.com/rholappa/views-forecast-api
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

## Working with Official VIEWS Forecast Drops

1. **Download the raw files** – grab the PRIO-GRID CSV (`fatalities*_pgm.csv`), the country-month CSV (`fatalities*_cm.csv`), and the forecast parquet pair (`preds_001*.parquet`). Drop them under `data/views_raw/<year>/<month>/` and `data/views_parquet/<year>/<month>/` respectively.
2. **Generate the API parquet** – convert the raw files into the schema expected by the service:
   ```bash
   venv/bin/python scripts/prepare_views_forecasts.py \
     --pgm-csv data/views_raw/2025/07/fatalities002_2025_07_t01_pgm.csv \
     --cm-csv  data/views_raw/2025/07/fatalities002_2025_07_t01_cm.csv \
     --preds-parquet "data/views_parquet/2025/07/preds_001 (1).parquet" \
     --hdi-parquet data/views_parquet/2025/07/preds_001_90_hdi.parquet \
     --output data/views_parquet/2025/07/api_ready/forecasts.parquet \
     --overwrite
   ```
3. **Point the API at the converted data** – copy `.env.example` to `.env` (if you haven’t already) and set:
   ```env
   USE_LOCAL_DATA=true
   DATA_PATH=data/views_parquet/2025/07/api_ready
   API_KEY=your-local-api-key
   ```
   Restart `make dev` after any change so the loader drops its cache.
4. **Call the API locally** – every request must include `X-API-Key: your-local-api-key` when `API_KEY` is set. Example:
   ```bash
   curl -H "X-API-Key: your-local-api-key" \
        "http://localhost:8000/api/v1/forecasts?country=MEX&months=2025-08"
   ```
   The repo ships a Bruno workspace in `views-forecast-api-bruno/`; import it and update the environment with your key to exercise the endpoints quickly.
5. **Refresh data** – rerun the conversion script whenever you download a new drop, then restart the server or clear the cache with:
   ```bash
   venv/bin/python - <<'PY'
   from app.services.data_loader import data_loader
   data_loader.cache.clear()
   PY
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

## Future Enhancements

The API is designed to easily support:
- Aggregation endpoints for regional summaries
- Administrative boundary queries
- Time series analysis endpoints
- Webhook notifications for new data
- GraphQL interface
- Real-time WebSocket updates

## License

This project is free to use for educational purposes.

## Support

For issues and questions, please open an issue in the repository.

## Authors

views-forecast-api / rauha.api is developed for the **VIEWS Challenge: Turning Conflict Forecasts into Accessible APIs** at **JunctionX Oulu 2025**.

Developed by:
- **Risto Holappa** - [GitHub](https://github.com/RHolappa)
- **Sillah Babar** - [GitHub](https://github.com/Sillah-Babar)

### Event
[JunctionX Oulu 2025](https://eu.junctionplatform.com/)

---

*This project was created as part of the VIEWS Challenge hackathon, focusing on making conflict forecasting data more accessible through API development.*
