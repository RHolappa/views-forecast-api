PYTHON ?= python

.PHONY: help install run dev test lint format clean docker-build docker-run db-load db-clean

help:
	@echo "Available commands:"
	@echo "  make install     - Install dependencies"
	@echo "  make run        - Run the API server"
	@echo "  make dev        - Run in development mode with auto-reload"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linting"
	@echo "  make format     - Format code"
	@echo "  make clean      - Clean cache and temporary files"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run  - Run Docker container"
	@echo "  make db-load     - Load parquet data into SQLite"
	@echo "  make db-clean    - Remove the SQLite database file"

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) -m app.main

dev:
	@DATA_BACKEND=$$($(PYTHON) -c "from app.core.config import settings; print(settings.data_backend)"); \
	if [ "$$DATA_BACKEND" = "database" ]; then \
		$(PYTHON) scripts/load_parquet_to_db.py --skip-if-exists; \
	else \
		$(PYTHON) scripts/bootstrap_local_data.py; \
	fi
	$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	ruff check app/ tests/

format:
	black app/ tests/
	ruff check app/ tests/ --fix

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov

docker-build:
	docker build -t views-forecast-api:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env views-forecast-api:latest

db-load:
	$(PYTHON) scripts/load_parquet_to_db.py \
		$(if $(SOURCE),--source "$(SOURCE)",) \
		$(if $(DB_URL),--database-url "$(DB_URL)",) \
		$(if $(MODE),--mode "$(MODE)",) \
		$(if $(SKIP_IF_EXISTS),--skip-if-exists,) \
		$(if $(RESET_DB),--reset-db,) \
		$(if $(S3_BUCKET),--s3-bucket "$(S3_BUCKET)",) \
		$(if $(S3_PREFIX),--s3-prefix "$(S3_PREFIX)",) \
		$(foreach key,$(S3_KEYS),--s3-key "$(key)" )

db-clean:
	@printf '%s\n' \
		"import os" \
		"from app.core.config import settings" \
		"from app.services.db_utils import sqlite_path_from_url" \
		"" \
		"db_url = os.environ.get('DB_URL') or settings.database_url" \
		"path = sqlite_path_from_url(db_url)" \
		"if path.exists():" \
		"    path.unlink()" \
		"    print(f'Removed SQLite database at {path}')" \
		"else:" \
		"    print(f'No SQLite database found at {path}')" \
		| $(PYTHON)
