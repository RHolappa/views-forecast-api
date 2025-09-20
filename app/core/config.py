import json
from typing import List, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v

    @field_validator("data_backend", mode="before")
    @classmethod
    def normalize_data_backend(cls, v, values):
        if isinstance(v, str) and v:
            return v.lower()

        # Fall back to legacy USE_LOCAL_DATA toggle when DATA_BACKEND is unset
        use_local = values.get("use_local_data")
        if use_local is False:
            return "cloud"

        return "parquet"

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
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
