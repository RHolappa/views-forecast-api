# VIEWS Conflict Forecast API

Open-source FastAPI service that exposes the VIEWS conflict forecasting dataset through a  REST API. The service is designed for analysts and engineers who need reproducible access to monthly conflict forecasts at the grid or country level.

## Contents
- [Features](#features)
- [Quick Start](#quick-start)
- [API Documentation & Examples](#api-documentation--examples)
- [Data Backends](#data-backends)
- [Testing & Quality](#testing--quality)
- [Docker](#docker)
- [Bruno Collection](#bruno-collection)
- [CI/CD & Deployment](#cicd--deployment)
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
These steps work on macOS, Linux, Windows (PowerShell or Git Bash), and Windows Subsystem for Linux. Windows-specific commands are noted where they differ.

### 1. Prerequisites
### 1. Prerequisites
- Python 3.11+
- Git 2.30+
- Optional: GNU Make (convenience targets). On Windows install via `winget install GnuWin32.Make`, `choco install make`, or use the "Without make" commands provided below.
- Git 2.30+
- Optional: GNU Make (convenience targets). On Windows install via `winget install GnuWin32.Make`, `choco install make`, or use the "Without make" commands provided below.

### 2. Clone the repository
```bash
git clone https://github.com/rholappa/views-forecast-api
cd views-forecast-api
```
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
### 3. Create a virtual environment
```bash
# macOS / Linux / WSL
python3 -m venv .venv
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
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5. Configure environment variables
```bash
cp .env.example .env          # macOS / Linux / WSL
Copy-Item .env.example .env   # Windows PowerShell
cp .env.example .env          # macOS / Linux / WSL
Copy-Item .env.example .env   # Windows PowerShell
```
Update `.env` with your desired configuration. Set `API_KEY` to the key you will use when calling the API. Uncomment and fill the `CLOUD_*` variables if you have access to the upstream parquet bucket, and provide `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` when the S3 bucket requires signed access.

### 6. Load sample or real data (optional but recommended)
If you keep `USE_LOCAL_DATA=true`, the dev server can bootstrap synthetic sample data automatically. To pull parquet files into SQLite:
### 6. Load sample or real data (optional but recommended)
If you keep `USE_LOCAL_DATA=true`, the dev server can bootstrap synthetic sample data automatically. To pull parquet files into SQLite:
```bash
make db-load                # add RESET_DB=1 to refresh
make db-load                # add RESET_DB=1 to refresh
```
Without make:
Without make:
```bash
python scripts/load_parquet_to_db.py --skip-if-exists
```

### 7. Run the API (development mode)
python scripts/load_parquet_to_db.py --skip-if-exists
```

### 7. Run the API (development mode)
```bash
make dev
```
Without make:
make dev
```
Without make:
```bash
python scripts/load_parquet_to_db.py --skip-if-exists
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
The API will be available at `http://localhost:8000` with hot reload enabled.

### 8. Smoke test
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
     "http://localhost:8000/api/v1/metadata/months"
```
A JSON array of months indicates your environment is ready.

## API Documentation & Examples
- Interactive docs: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`
## API Documentation & Examples
- Interactive docs: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

Example queries:
```bash
# All grid cells for a country
Example queries:
```bash
# All grid cells for a country
curl -H "X-API-Key: your-local-api-key" \
     "http://localhost:8000/api/v1/forecasts?country=074"
     "http://localhost:8000/api/v1/forecasts?country=074"

# Specific grid IDs within a month range and selected metrics
# Specific grid IDs within a month range and selected metrics
curl -H "X-API-Key: your-local-api-key" \
     "http://localhost:8000/api/v1/forecasts?grid_ids=12001001&grid_ids=12001002&month_range=2025-08:2025-12&metrics=map&metrics=ci_90_low&metrics=ci_90_high"
     "http://localhost:8000/api/v1/forecasts?grid_ids=12001001&grid_ids=12001002&month_range=2025-08:2025-12&metrics=map&metrics=ci_90_low&metrics=ci_90_high"

# Thresholds on metrics
# Thresholds on metrics
curl -H "X-API-Key: your-local-api-key" \
     "http://localhost:8000/api/v1/forecasts?country=074&metric_filters=map>50&metric_filters=prob_1000>=0.1"
```
For hosted deployments replace the base URL (`http://localhost:8000`) with the production endpoint.

## Data Backends
- `.env` controls how data is sourced. Key variables:
  - `USE_LOCAL_DATA=true` keeps data in parquet form; a synthetic dataset is generated on demand if no files exist.
  - `DATA_BACKEND=database` (default) stores data in SQLite at `DATABASE_URL`.
  - `DATA_PATH` points to local parquet directories. Update it if you have real parquet files.
- Set `CLOUD_BUCKET_NAME`, `CLOUD_DATA_PREFIX`, and optional `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `CLOUD_BUCKET_REGION` to fetch parquet files from object storage.
- Automated bootstrapping is controlled by `AUTO_LOAD_DATA`, `RESET_DB_ON_START`, and `SKIP_DB_IF_EXISTS`. These flags are honoured by the Docker entrypoint and any shell that sources `.env`.
- To refresh the database use `make db-load RESET_DB=1` or run `python scripts/load_parquet_to_db.py --reset-db` manually.
- Use `make db-clean` to delete the SQLite file entirely.

## Testing & Quality
## Testing & Quality
```bash
make test     # pytest with coverage
make lint     # ruff checks
make format   # black + ruff --fix
make test     # pytest with coverage
make lint     # ruff checks
make format   # black + ruff --fix
```
Without make:
Without make:
```bash
python -m pytest tests/ -v --cov=app --cov-report=term-missing
ruff check app/ tests/
black app/ tests/
ruff check app/ tests/ --fix
```

## Docker
- **Build the image**:
  ```bash
  docker build -t views-forecast-api:latest .
  ```
- **Run a container** with your `.env` file:
  ```bash
  docker run --rm -p 8000:8000 --env-file .env \
             -v $(pwd)/data:/app/data \
             views-forecast-api:latest
  ```
  The entrypoint hydrates SQLite on start when `AUTO_LOAD_DATA=true`, using S3 if credentials are present. Override `UVICORN_WORKERS` for multi-worker deployments and `RESET_DB_ON_START=1` when you need a fresh import.

### Docker Compose (local & production parity)
```bash
docker compose up --build -d
```
- Uses `.env` automatically and persists data in the named volume `forecasts-data`.
- Provide AWS credentials via `.env` or your secrets manager so the container can download parquet files on first boot.
- Toggle `UVICORN_RELOAD=1` for hot reload during container development; keep it at `0` in production.
- Set `UVICORN_WORKERS` (for example `4`) when deploying behind a load balancer.

## Bruno Collection
The Bruno workspace in `views-forecast-api-bruno/` includes ready-made requests for key endpoints. Open it in Bruno Desktop or run via the Bruno CLI after setting your `X-API-Key`.

## CI/CD & Deployment
- **GitHub Actions**: `.github/workflows/ci.yml` runs linting, tests (Python 3.9–3.12), and security scans on pushes, pull requests, and releases. Extend this pipeline with a release workflow that builds the Docker image and pushes to GHCR or Amazon ECR on tagged releases.
- **Environment secrets**: store `API_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `CLOUD_BUCKET_NAME` as repository or environment secrets so Actions can hydrate data during integration tests or image builds.
- **AWS deployment (future)**:
  - Push container images to Amazon ECR and deploy to AWS Fargate (ECS) or App Runner.
  - Back persistent storage with an EFS volume or migrate to a managed database (Aurora/PostgreSQL) by updating `DATABASE_URL`.
  - Inject configuration through AWS Systems Manager Parameter Store or Secrets Manager. The same `.env` keys map directly to task definitions or service configuration.
  - Automate promotion with a GitHub Actions CD workflow that triggers `aws ecs update-service` or `aws apprunner update-service` after CI passes.

## Project Resources
- [`CONTRIBUTING.md`](CONTRIBUTING.md) for development workflow guidelines.
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for community expectations.
- [`SECURITY.md`](SECURITY.md) for reporting vulnerabilities.
- [`CHANGELOG.md`](CHANGELOG.md) for release notes.
- Open issues or discussions on GitHub for help or feature requests.

## License
Distributed under the [MIT License](LICENSE).
Distributed under the [MIT License](LICENSE).

## Maintainers & Origin
Created for the VIEWS Challenge at JunctionX Oulu 2025 and maintained by:
- [Risto Holappa](https://github.com/RHolappa)
- [Sillah Babar](https://github.com/Sillah-Babar)
## Maintainers & Origin
Created for the VIEWS Challenge at JunctionX Oulu 2025 and maintained by:
- [Risto Holappa](https://github.com/RHolappa)
- [Sillah Babar](https://github.com/Sillah-Babar)

We welcome contributions that help make conflict forecasting data more accessible.
We welcome contributions that help make conflict forecasting data more accessible.
