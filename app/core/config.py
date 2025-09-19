import json

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
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    # Cloud Storage
    cloud_bucket_name: str | None = Field(
        default=None, description="Cloud bucket name for data storage"
    )
    cloud_bucket_region: str = Field(default="us-east-1", description="AWS region")
    aws_access_key_id: str | None = Field(default=None, description="AWS access key")
    aws_secret_access_key: str | None = Field(default=None, description="AWS secret key")

    # Cache Configuration
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")
    cache_max_size: int = Field(default=1000, description="Maximum cache size")

    # Optional API Authentication
    api_key: str | None = Field(default=None, description="Optional API key for authentication")

    # Data Configuration
    data_path: str = Field(default="data/sample", description="Path to local data")
    use_local_data: bool = Field(default=True, description="Use local data instead of cloud")

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
