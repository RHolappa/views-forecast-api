PYTHON ?= python

.PHONY: help install run dev test lint format clean docker-build docker-run

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

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) -m app.main

dev:
	$(PYTHON) scripts/bootstrap_local_data.py
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
