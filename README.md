# VIEWS Conflict Forecast API

Open-source FastAPI service that exposes the VIEWS conflict forecasting dataset through a clean, well-documented REST API. The service is designed for analysts and engineers who need reproducible access to monthly conflict forecasts at the grid or country level.

## Contents
- [Features](#features)
- [Quick Start](#quick-start)
- [API Documentation & Examples](#api-documentation--examples)
- [Data Backends](#data-backends)
- [Testing & Quality](#testing--quality)
- [Docker](#docker)
- [Bruno Collection](#bruno-collection)
- [Project Resources](#project-resources)
- [License](#license)
- [Maintainers & Origin](#maintainers--origin)

## Features
- FastAPI server with automatic OpenAPI documentation and interactive docs UI.
- SQLite-backed data store by default, with support for parquet files and S3 as sources.
- Rich filtering options (country, grid, months, metrics, thresholds) for fine-grained queries.
- Bruno workspace and `curl` examples for quick integrations and manual testing.

## Quick Start
These steps work on macOS, Linux, Windows (PowerShell or Git Bash), and Windows Subsystem for Linux. Windows-specific commands are noted where they differ.

### 1. Prerequisites
- Python 3.11+
- Git 2.30+
- Optional: GNU Make (convenience targets). On Windows install via `winget install GnuWin32.Make`, `choco install make`, or use the "Without make" commands provided below.

### 2. Clone the repository
```bash
git clone https://github.com/rholappa/views-forecast-api
cd views-forecast-api
```

### 3. Create a virtual environment
```bash
# macOS / Linux / WSL
python3.11 -m venv .venv
source .venv/bin/activate
```
```powershell
# Windows (PowerShell)
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
# If activation is blocked, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. Install dependencies
```bash
make install
```
Without make:
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5. Configure environment variables
```bash
cp .env.example .env          # macOS / Linux / WSL
Copy-Item .env.example .env   # Windows PowerShell
```
Update `.env` with your desired configuration. Set `API_KEY` to the key you will use when calling the API. Uncomment and fill the `CLOUD_*` variables if you have access to the upstream parquet bucket.

### 6. Load sample or real data (optional but recommended)
If you keep `USE_LOCAL_DATA=true`, the dev server can bootstrap synthetic sample data automatically. To pull parquet files into SQLite:
```bash
make db-load                # add RESET_DB=1 to refresh
```
Without make:
```bash
python scripts/load_parquet_to_db.py --skip-if-exists
```

### 7. Run the API (development mode)
```bash
make dev
```
Without make:
```bash
python scripts/load_parquet_to_db.py --skip-if-exists
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
The API will be available at `http://localhost:8000` with hot reload enabled.

### 8. Smoke test
```bash
curl -H "X-API-Key: your-local-api-key" \
     "http://localhost:8000/api/v1/metadata/months"
```
A JSON array of months indicates your environment is ready.

## API Documentation & Examples
- Interactive docs: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

Example queries:
```bash
# All grid cells for a country
curl -H "X-API-Key: your-local-api-key" \
     "http://localhost:8000/api/v1/forecasts?country=074"

# Specific grid IDs within a month range and selected metrics
curl -H "X-API-Key: your-local-api-key" \
     "http://localhost:8000/api/v1/forecasts?grid_ids=12001001&grid_ids=12001002&month_range=2025-08:2025-12&metrics=map&metrics=ci_90_low&metrics=ci_90_high"

# Thresholds on metrics
curl -H "X-API-Key: your-local-api-key" \
     "http://localhost:8000/api/v1/forecasts?country=074&metric_filters=map>50&metric_filters=prob_1000>=0.1"
```

## Data Backends
- `.env` controls how data is sourced. Key variables:
  - `USE_LOCAL_DATA=true` keeps data in parquet form; a synthetic dataset is generated on demand if no files exist.
  - `DATA_BACKEND=database` (default) stores data in SQLite at `DATABASE_URL`.
  - `DATA_PATH` points to local parquet directories. Update it if you have real parquet files.
- To refresh the database use `make db-load RESET_DB=1` or run `python scripts/load_parquet_to_db.py --reset-db` manually.
- Use `make db-clean` to delete the SQLite file entirely.

## Testing & Quality
```bash
make test     # pytest with coverage
make lint     # ruff checks
make format   # black + ruff --fix
```
Without make:
```bash
python -m pytest tests/ -v --cov=app --cov-report=term-missing
ruff check app/ tests/
black app/ tests/
ruff check app/ tests/ --fix
```

## Docker
```bash
make docker-build
make docker-run             # exposes the API on port 8000 and reads .env
```
With Docker Compose:
```bash
docker compose up --build
```

## Bruno Collection
The Bruno workspace in `views-forecast-api-bruno/` includes ready-made requests for key endpoints. Open it in Bruno Desktop or run via the Bruno CLI after setting your `X-API-Key`.

## Project Resources
- [`CONTRIBUTING.md`](CONTRIBUTING.md) for development workflow guidelines.
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for community expectations.
- [`SECURITY.md`](SECURITY.md) for reporting vulnerabilities.
- [`CHANGELOG.md`](CHANGELOG.md) for release notes.
- Open issues or discussions on GitHub for help or feature requests.

## License
Distributed under the [MIT License](LICENSE).

## Maintainers & Origin
Created for the VIEWS Challenge at JunctionX Oulu 2025 and maintained by:
- [Risto Holappa](https://github.com/RHolappa)
- [Sillah Babar](https://github.com/Sillah-Babar)

We welcome contributions that help make conflict forecasting data more accessible.
