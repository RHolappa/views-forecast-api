"""Application configuration management.

This module handles all configuration settings for the VIEWS Forecast API,
including API server configuration, data backend settings, cloud storage
configuration, and environment-specific settings. Configuration values can
be provided via environment variables or a .env file.
"""

import json
from typing import List, Literal, Optional

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings.

    This class manages all configuration for the VIEWS Forecast API using
    Pydantic for validation and environment variable loading. Settings can
    be provided via environment variables, a .env file, or defaults.

    Attributes:
        api_host: Host address for the API server.
        api_port: Port number for the API server.
        api_v1_prefix: URL prefix for API v1 endpoints.
        environment: Deployment environment (development/staging/production).
        cors_origins: List of allowed CORS origins.
        cloud_bucket_name: Optional S3 bucket name for cloud data storage.
        cloud_bucket_region: AWS region for cloud storage.
        cloud_data_prefix: Path prefix within cloud bucket.
        cloud_data_key: Specific object key for cloud data.
        aws_access_key_id: AWS access key for authentication.
        aws_secret_access_key: AWS secret key for authentication.
        cache_ttl_seconds: Cache time-to-live in seconds.
        cache_max_size: Maximum number of cached items.
        api_key: Optional API key for endpoint authentication.
        data_path: Path to local data directory.
        use_local_data: Legacy flag for local data usage.
        data_backend: Storage backend type (parquet/database/cloud).
        database_url: Database connection URL.
        log_level: Logging verbosity level.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")

    # Environment
    environment: str = Field(
        default="development", description="Environment (development, staging, production)"
    )

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    # Cloud Storage
    cloud_bucket_name: Optional[str] = Field(
        default=None, description="Cloud bucket name for data storage"
    )
    cloud_bucket_region: str = Field(default="eu-north-1", description="AWS region")
    cloud_data_prefix: Optional[str] = Field(
        default="api_ready/", description="Prefix within the cloud bucket for forecast data"
    )
    cloud_data_key: Optional[str] = Field(
        default=None, description="Specific object key to load from the cloud bucket"
    )
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret key")

    # Cache Configuration
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")
    cache_max_size: int = Field(default=1000, description="Maximum cache size")

    # Optional API Authentication
    api_key: Optional[str] = Field(default=None, description="Optional API key for authentication")

    # Data Configuration
    data_path: str = Field(default="data/sample", description="Path to local data")
    use_local_data: bool = Field(default=False, description="Use local data instead of cloud")
    data_backend: Literal["parquet", "database", "cloud"] = Field(
        default="database",
        description="Storage backend for forecasts",
    )
    database_url: str = Field(
        default="sqlite:///data/forecasts.db",
        description="Database URL used when DATA_BACKEND=database",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON string or list.

        Handles CORS origins provided as either a JSON-encoded string
        (common in environment variables) or a Python list.

        Args:
            v: Raw CORS origins value (string or list).

        Returns:
            List of CORS origin URLs.
        """
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v

    @field_validator("data_backend", mode="before")
    @classmethod
    def normalize_data_backend(cls, v, info: ValidationInfo):
        """Normalize data backend configuration with fallback logic.

        Converts backend string to lowercase and applies legacy fallback
        logic for USE_LOCAL_DATA flag when DATA_BACKEND is not set.

        Args:
            v: Raw data backend value.
            values: Other field values for fallback logic.

        Returns:
            Normalized backend identifier (parquet/database/cloud).
        """
        if isinstance(v, str) and v:
            return v.lower()

        prior_values = info.data or {}
        use_local = prior_values.get("use_local_data")
        if use_local is False:
            return "cloud"

        return "parquet"

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment is one of allowed values.

        Ensures the environment setting is restricted to known
        deployment environments.

        Args:
            v: Environment value to validate.

        Returns:
            Validated environment string.

        Raises:
            ValueError: If environment is not in allowed set.
        """
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


settings = Settings()
