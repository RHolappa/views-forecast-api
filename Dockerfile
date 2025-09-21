FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies required for pandas/pyarrow and clean up apt caches
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definitions first to leverage Docker layer caching
COPY requirements.txt ./

RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy the full project (includes scripts for data bootstrap)
COPY . .

# Ensure runtime directories exist
RUN mkdir -p data/sample \
    && chmod +x scripts/docker-entrypoint.sh

# Switch to a non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
