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
          # This will create sample data if not found 
# or
make run  # Production mode
```

The API will be available at `http://localhost:8000`


## Working with Official VIEWS Forecast Drops

For quick local exploration, run `make dev` (or `python scripts/bootstrap_local_data.py`) to accept the prompt that generates a synthetic `sample_data.parquet` in the correct schema. (Pandera used)

1. **Import** – download the raw parquet pair from VIEWS for example: (`preds_001.parquet` and `preds_001_90_hdi.parquet`) and drop them under `data/views_raw/<year>/<month>/`. The repository ships an example in `data/views_raw/2025/07/`.
2. **Prepare** – convert the draws into the API schema. The script reads the raw parquets only, expands the forecast draws into summary statistics, and validates the output with Pandera before writing the parquet:
   ```bash
   venv/bin/python scripts/prepare_views_forecasts.py \
     --preds-parquet data/views_raw/2025/07/preds_001.parquet \
     --hdi-parquet   data/views_raw/2025/07/preds_001_90_hdi.parquet \
     --output        data/views_parquet/2025/07/api_ready/forecasts.parquet \
     --overwrite
   ```
   The resulting parquet stores int32 grid identifiers, zero-padded country codes, and float32 metrics/probabilities so the API loader can stream the data efficiently.
3. **Use** – point the API at the converted data by copying `.env.example` to `.env` (if you haven’t already) and set:
   ```env
   USE_LOCAL_DATA=true
   DATA_PATH=data/views_parquet/2025/07/api_ready
   API_KEY=your-local-api-key
   ```
   Restart `make dev` after any change so the loader drops its cache.
4. **Call the API locally** – every request must include `X-API-Key: your-local-api-key` when `API_KEY` is set. Example:
   ```bash
   curl -H "X-API-Key: your-local-api-key" \
        "http://localhost:8000/api/v1/forecasts?country=074&months=2025-08"
   ```
   The repo ships a Bruno workspace in `views-forecast-api-bruno/`; import it and update the environment with your key to exercise the endpoints quickly.
5. **Refresh data** – rerun the conversion script whenever you download a new drop, then restart the server or clear the cache with:
   ```bash
   venv/bin/python - <<'PY'
   from app.services.data_loader import data_loader
   data_loader.cache.clear()
   PY
   ```

## API Capabilities
Make sure you have the X-API-Key header used based on the env file
- Metadata coverage: months and grid cells are exposed via `/api/v1/metadata/months` and `/api/v1/metadata/grid-cells`.
- Country-wide retrieval: `GET /api/v1/forecasts?country=074` returns every grid cell in the country with the standard 13 metrics (UN M49 code `074` = region example).
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
- `country`: UN M49 numeric country code (zero-padded, e.g., `074`)
- `grid_ids`: List of grid cell IDs
- `months`: Specific months (YYYY-MM format)
- `month_range`: Range of months (YYYY-MM:YYYY-MM)
- `metrics`: Specific metrics to return
- `format`: Response format (json or ndjson)

Example:
```bash
curl "http://localhost:8000/api/v1/forecasts?country=074&months=2024-01&metrics=map&metrics=ci_90_low&metrics=ci_90_high"
```

Each forecast row includes `grid_id`, centroid latitude/longitude, the UN M49 `country_id`, and optional `admin_1_id` and `admin_2_id` fields.

#### Get Available Months
```bash
GET /api/v1/metadata/months
```

Returns all months with available forecast data.

#### Get Grid Cells
```bash
GET /api/v1/metadata/grid-cells?country=074
```

Returns grid cells, optionally filtered by country. Each record includes the grid ID, centroid lat/lon, the UN M49 country code, and admin identifiers when available.

## Data Storage

The API supports two data storage modes:

### Local Data (Development)
- Set `USE_LOCAL_DATA=true` in `.env` (defaults to `true`) and point `DATA_PATH` at the folder that holds your parquet files (defaults to `data/sample`).
- Run `make dev` – if no parquet files exist the task will offer to generate a synthetic dataset that mirrors the API schema (`sample_data.parquet` under `DATA_PATH`).
- You can manually regenerate the sample dataset at any time with `python scripts/bootstrap_local_data.py`.

### Cloud Storage (Production)
- Set `USE_LOCAL_DATA=false`
- Configure S3 credentials in `.env` using `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (or rely on the default credential chain inside your deployment environment).
- Point `CLOUD_BUCKET_NAME` at the bucket that stores parquet files and use either `CLOUD_DATA_KEY` for a single parquet object (for example `api_ready/forecasts.parquet`) or `CLOUD_DATA_PREFIX` to load every parquet under a folder.
- The loader downloads parquet objects directly from S3 using `boto3`; ensure the IAM role or user has `s3:ListBucket` and `s3:GetObject` permissions for the configured bucket.

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
