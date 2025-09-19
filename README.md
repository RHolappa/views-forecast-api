# VIEWS Conflict Forecast API

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

## API Capabilities
Make sure you have the X-API-Key header used based on the env file
- Metadata coverage: months and grid cells are exposed via `/api/v1/metadata/months` and `/api/v1/metadata/grid-cells`.
- Country-wide retrieval: `GET /api/v1/forecasts?country=UGA` returns every grid cell in the country with the standard 13 metrics.
- Targeted grid lookups: use `grid_ids` with one or many IDs to pull specific cells alongside other filters.
- Temporal slicing: apply `months=YYYY-MM` or `month_range=YYYY-MM:YYYY-MM` to focus on single months or contiguous ranges.
- Metric selection: repeat the `metrics` parameter (e.g., `metrics=map`) to limit the payload to the values you need.
- Response formats and metadata: choose `format=json` or `format=ndjson`; each record includes the grid ID, centroid latitude/longitude, UN M49 country ID, and optional Admin-1/Admin-2 identifiers.

## API Documentation

Once running, visit:
- **Interactive API docs**: http://localhost:8000/docs
- **OpenAPI schema**: http://localhost:8000/openapi.json

### Bruno
https://www.usebruno.com/

The Bruno workspace in `views-forecast-api-bruno/` ships ready-made requests for the capabilities above—open it in Bruno Desktop or run with the CLI after setting your API key.

(X-API-Key header from env file needed)

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

Each forecast row includes `grid_id`, centroid latitude/longitude, the UN M49 `country_id`, and optional `admin_1_id` and `admin_2_id` fields.

#### Get Available Months
```bash
GET /api/v1/metadata/months
```

Returns all months with available forecast data.

#### Get Grid Cells
```bash
GET /api/v1/metadata/grid-cells?country=UGA
```

Returns grid cells, optionally filtered by country. Each record includes the grid ID, centroid lat/lon, the UN M49 country code, and admin identifiers when available.

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
     --preds-parquet "data/views_parquet/2025/07/preds_001.parquet" \
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
