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
   python3 -m venv path/to/venv
   source path/to/venv/bin/activate
   ```

   ```bash
   make install
   cp .env.example .env
   ```

3. Now you can update / add the AWS credentials if needed. Contact us if you need read -access! S3 bucket have latest preds (07/25) parquet files uploaded and will be updated when possible.

4. Hydrate the local SQLite database and start the API:

   ```bash
   make db-load      # downloads & converts raw parquets into data/forecasts.db use  add RESET_DB=1 if old exists
                     # Skip this if you dont have CLOUD access!
   ```

   ```bash
   make dev          # API on http://localhost:8000
   ```

   Subsequent runs only need `make dev`; the loader skips re-importing when the DB already has rows.

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:

- **Interactive API docs**: <http://localhost:8000/docs>
- **OpenAPI schema**: <http://localhost:8000/openapi.json>

## API Capabilities

Make sure you have the X-API-Key header used based on the env file

- Metadata coverage: months and grid cells are exposed via `/api/v1/metadata/months` and `/api/v1/metadata/grid-cells`.
- Country-wide retrieval: `GET /api/v1/forecasts?country=074` returns every grid cell in the country with the standard 13 metrics (UN M49 code `074` = region example).
- Targeted grid lookups: use `grid_ids` with one or many IDs to pull specific cells alongside other filters.
- Temporal slicing: apply `months=YYYY-MM` or `month_range=YYYY-MM:YYYY-MM` to focus on single months or contiguous ranges.
- Metric selection: repeat the `metrics` parameter (e.g., `metrics=map`) to limit the payload to the values you need.
- Response formats and metadata: choose `format=json` or `format=ndjson`; each record includes the grid ID, centroid latitude/longitude, UN M49 country ID, and optional Admin-1/Admin-2 identifiers.


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

Examples:

**Query by country (all cells in a country):**
```bash
curl -H "X-API-Key: your-local-api-key" "http://localhost:8000/api/v1/forecasts?country=074"
```

**Query by specific grid cell IDs:**
```bash
curl -H "X-API-Key: your-local-api-key" "http://localhost:8000/api/v1/forecasts?grid_ids=12001001&grid_ids=12001002"
```

**Query by month or month range:**
```bash
# Single month
curl -H "X-API-Key: your-local-api-key" "http://localhost:8000/api/v1/forecasts?country=074&months=2025-09"

# Month range
curl -H "X-API-Key: your-local-api-key" "http://localhost:8000/api/v1/forecasts?country=074&month_range=2025-08:2025-12"
```

**Choose specific metrics (MAP, confidence intervals, probabilities):**
```bash
# All confidence intervals and probabilities
curl -H "X-API-Key: your-local-api-key" "http://localhost:8000/api/v1/forecasts?country=074&metrics=map&metrics=ci_50_low&metrics=ci_50_high&metrics=ci_90_low&metrics=ci_90_high&metrics=ci_99_low&metrics=ci_99_high&metrics=prob_100&metrics=prob_1000"

# Just MAP and 90% confidence interval
curl -H "X-API-Key: your-local-api-key" "http://localhost:8000/api/v1/forecasts?country=074&months=2025-09&metrics=map&metrics=ci_90_low&metrics=ci_90_high"
```

**Filter by metric thresholds (e.g. MAP > 50):**
```bash
curl -H "X-API-Key: your-local-api-key" "http://localhost:8000/api/v1/forecasts?country=074&metric_filters=map>50"

# Combine multiple filters
curl -H "X-API-Key: your-local-api-key" "http://localhost:8000/api/v1/forecasts?country=074&metric_filters=map>50&metric_filters=prob_1000>=0.1"
```

### Production deployment

Example (Deployed by Sillah)

```bash

curl -H "X-API-Key: your-local-api-key" \
"https://app-api-485850269158.europe-north1.run.app/api/v1/forecasts?country=074&metric_filters=map%3E50&metric_filters=prob_1000"

curl -H "X-API-Key: your-local-api-key" \
"https://app-api-485850269158.europe-north1.run.app/api/v1/forecasts?country=074&metric_filters=map"

curl -H "X-API-Key: your-local-api-key" \
"https://app-api-485850269158.europe-north1.run.app/api/v1/forecasts?country=074&months=2025-09&metrics=map&metrics=ci_90_low&metrics=ci_90_high"

curl -H "X-API-Key: your-local-api-key" \
"https://app-api-485850269158.europe-north1.run.app/api/v1/forecasts?country=074&metrics=map&metrics=ci_50_low&metrics=ci_50_high&metrics=ci_90_low&metrics=ci_90_high&metrics=ci_99_low&metrics=ci_99_high&metrics=prob_100&metrics=prob_1000"

curl -H "X-API-Key: your-local-api-key" \
"https://app-api-485850269158.europe-north1.run.app/api/v1/forecasts?country=074&month_range=2025-08:2025-12"

curl -H "X-API-Key: your-local-api-key" \
"https://app-api-485850269158.europe-north1.run.app/api/v1/forecasts?country=074&months=2025-09"

curl -H "X-API-Key: your-local-api-key" \
"https://app-api-485850269158.europe-north1.run.app/api/v1/forecasts?country=074"

curl -H "X-API-Key: your-local-api-key" \
"https://app-api-485850269158.europe-north1.run.app/api/v1/forecasts?grid_ids=12001001&grid_ids=12001002"

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
