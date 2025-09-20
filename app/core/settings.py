"""Application metadata and logging configuration.

This module sets up application-wide logging configuration and defines
metadata constants used throughout the VIEWS Forecast API, including
application name, version, description, and API documentation tags.
"""

import logging
import sys

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

# Application metadata
APP_NAME = "VIEWS Forecast API"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = """
VIEWS Conflict Forecast API provides grid-level conflict predictions with uncertainty quantification.

## Features
* Grid-cell level forecasts with 13 prediction metrics
* Country and region filtering
* Flexible time range queries
* Multiple response formats (JSON, NDJSON)
"""

# API Tags for documentation
tags_metadata = [
    {
        "name": "forecasts",
        "description": "Retrieve conflict forecast data",
    },
    {
        "name": "metadata",
        "description": "Get available months and grid cells",
    },
    {
        "name": "health",
        "description": "Health check endpoints",
    },
]
