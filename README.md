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

2. Install dependencies and bootstrap the environment:

   ```bash
   make install
   cp .env.example .env
   ```

3. Use the shared sandbox AWS credentials (temporary demo READ access to the bucket):

   ```bash
   export AWS_ACCESS_KEY_ID=AKIAVRUVRCKVGAMY5VNV
   export AWS_SECRET_ACCESS_KEY=KuscPWyOC8JPdWSmNN0Xc4kUgYAaT1YaErdu1jI8
   ```

   > These credentials are intentionally public for now so everyone can pull the actual VIEWS S3 drop. Also there is fallback to sample_data if not working anymore

4. Hydrate the local SQLite database and start the API:

   ```bash
   make db-load      # downloads & converts raw parquets into data/forecasts.db use  RESET_DB=1 if old exists
   make dev          # API on http://localhost:8000
   ```

   Subsequent runs only need `make dev`; the loader skips re-importing when the DB already has rows.

The API will be available at `http://localhost:8000`

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

- **Interactive API docs**: <http://localhost:8000/docs>
- **OpenAPI schema**: <http://localhost:8000/openapi.json>

### Bruno

<https://www.usebruno.com/>

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
curl -H "X-API-Key: your-local-api-key" "http://localhost:8000/api/v1/forecasts?country=074&months=2024-01&metrics=map&metrics=ci_90_low&metrics=ci_90_high"
```
or:

```bash
curl -H "X-API-Key: your-local-api-key" "http://localhost:8000/api/v1/forecasts?country=074"
```

## Data Storage

The API supports these data storage modes:

### Local Data (Development)

- Set `USE_LOCAL_DATA=true` in `.env` (defaults to `false`) and point `DATA_PATH` at the folder that holds your parquet files (defaults to `data/sample`).
- Run `make dev` – if no parquet files exist the task will offer to generate a synthetic dataset that mirrors the API schema (`sample_data.parquet` under `DATA_PATH`).
- You can manually regenerate the sample dataset at any time with `python scripts/bootstrap_local_data.py`.

### SQLite Database (Default for Local Runs)

- `DATA_BACKEND=database` is the default; adjust `DATABASE_URL` if you want a custom path (defaults to `sqlite:///data/forecasts.db`).
- `make dev` automatically downloads parquet files from `CLOUD_*` settings and hydrates the SQLite database the first time (or whenever the file is missing).
- Load parquet files manually with `make db-load`:
  - `SOURCE=/path/to/parquet` reads from disk.
  - `S3_BUCKET=... S3_PREFIX=...` (or `S3_KEYS="key1 key2"`) downloads parquet objects from S3 first.
  - `SKIP_IF_EXISTS=1` prevents re-importing when `forecasts` already has rows.
  - `RESET_DB=1` removes the SQLite file before loading.
  - `MODE=append` appends instead of replacing.
- Use `make db-clean` (or `python scripts/load_parquet_to_db.py --reset-db`) when you want to remove the SQLite file and start fresh.
- When refreshing data, re-run `make db-load MODE=replace` (default) or `MODE=append` depending on your workflow.

### Cloud Storage (Production)

- Set `USE_LOCAL_DATA=false` and/or `DATA_BACKEND=cloud`.
- Configure S3 credentials in `.env` using `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (or rely on the default credential chain inside your deployment environment). For quick demos you can export the shared sandbox keys shown in the quick-start section.
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
