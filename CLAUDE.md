# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI-based REST API for serving grid-level conflict forecasts with uncertainty quantification. The API provides forecast data with 13 different prediction metrics including confidence intervals and probability thresholds for different fatality levels.

## Development Commands

### Setup & Installation
```bash
make install          # Install dependencies from requirements.txt
cp .env.example .env   # Copy environment template (edit as needed)
```

### Running the API
```bash
make dev              # Development mode with auto-reload (uvicorn)
make run              # Production mode (python -m app.main)
```

### Code Quality & Testing
```bash
make test             # Run pytest with coverage (pytest tests/ -v --cov=app --cov-report=term-missing)
make lint             # Run ruff linting (ruff check app/ tests/)
make format           # Format with black and fix with ruff
pytest tests/test_api.py::test_specific_function  # Run single test
```

### Docker
```bash
make docker-build     # Build Docker image
make docker-run       # Run container
docker-compose up -d  # Using docker-compose
```

## Architecture

### Core Structure
- **FastAPI Application**: Entry point in `app/main.py` with lifespan management
- **Three-Layer Architecture**:
  - API routes (`app/api/routes/`) handle HTTP requests
  - Services (`app/services/`) contain business logic
  - Models (`app/models/`) define data structures with Pydantic

### Key Components

**Data Layer**:
- `DataLoader` class (`app/services/data_loader.py`) manages data access with TTL caching
- Supports both local Parquet files (`data/sample/`) and cloud storage (configurable)
- Auto-generates sample data if no files found locally

**API Layer**:
- `/api/v1/forecasts` - Main forecast endpoint with flexible filtering
- `/api/v1/metadata/*` - Metadata endpoints for months and grid cells
- Supports both JSON and NDJSON streaming responses
- Optional API key authentication via dependency injection

**Configuration**:
- Pydantic Settings (`app/core/config.py`) with `.env` file support
- Validates environment values and provides computed properties
- Handles CORS origins as JSON array or single string

### Data Model
Forecasts contain 13 metrics per grid cell/month:
- `map`: Most Accurate Prediction
- Confidence intervals: `ci_50_low/high`, `ci_90_low/high`, `ci_99_low/high`
- Probability thresholds: `prob_0`, `prob_1`, `prob_10`, `prob_100`, `prob_1000`, `prob_10000`

## Key Implementation Details

### Query Processing
The `ForecastQuery` model supports:
- Country filtering (ISO 3166-1 alpha-3 codes)
- Grid cell ID lists
- Month lists or ranges (YYYY-MM format)
- Metric selection for partial responses

### Caching Strategy
- TTL cache in DataLoader with configurable size/duration
- Single cache key for all data (simple but effective for current scale)
- Cache invalidation on data reload

### Error Handling
- Global exception handler in main.py
- Development vs production error detail levels
- Proper HTTP status codes with structured error responses

### Testing Structure
- `tests/test_api.py` - FastAPI endpoint testing
- `tests/test_models.py` - Pydantic model validation
- `tests/test_services.py` - Business logic testing
- Uses pytest with async support and coverage reporting

## Environment Variables

Key configuration (see `.env.example`):
- `USE_LOCAL_DATA=true` - Use local Parquet files vs cloud storage
- `DATA_PATH=data/sample` - Local data directory
- `API_KEY` - Optional authentication
- `CACHE_TTL_SECONDS=3600` - Cache duration
- `ENVIRONMENT=development` - Affects error verbosity

## Code Style

- Line length: 100 characters (black + ruff)
- Python 3.11+ target
- Ruff linting with pycodestyle, flake8-bugbear, isort, pyupgrade
- Type hints required for service layer functions
- Async/await pattern for all route handlers