"""Data loading service for forecast data from multiple backends.

This module handles loading forecast data from various storage backends
including SQLite databases, parquet files, and cloud storage (S3). It provides
a unified interface for data access with caching support for performance.
"""

import io
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from cachetools import TTLCache

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ModuleNotFoundError:  # pragma: no cover - boto3 optional for local workflows
    boto3 = None
    BotoCoreError = ClientError = Exception

from app.core.config import settings
from app.models.forecast import ALL_METRIC_NAMES, ForecastMetrics, GridCellForecast, MetricName
from app.services.data_initializer import ensure_local_data_ready
from app.services.db_utils import sqlite_path_from_url
from app.services.sample_data import FORECAST_COLUMNS, generate_sample_forecasts

logger = logging.getLogger(__name__)


class DataLoader:
    """Main data loading class supporting multiple storage backends.

    Provides unified data access for forecast data stored in SQLite databases,
    parquet files, or cloud storage. Includes caching for performance optimization
    and automatic initialization of the appropriate storage backend.

    Attributes:
        cache: TTL cache for storing loaded data.
        data_path: Path to local data directory.
        backend: Storage backend type (database/parquet/cloud).
        _data: Cached DataFrame of forecast data.
        _s3_client: AWS S3 client for cloud storage access.
        _db_path: Path to SQLite database file.
    """

    def __init__(self):
        """Initialize data loader with configured backend."""
        self.cache = TTLCache(maxsize=settings.cache_max_size, ttl=settings.cache_ttl_seconds)
        self.data_path = Path(settings.data_path)
        self.backend = settings.data_backend
        self._data: Optional[pd.DataFrame] = None
        self._s3_client = None
        self._db_path: Optional[Path] = None

        if self.backend == "cloud" and self._should_use_sample_backend():
            logger.warning(
                "Falling back to sample data because USE_LOCAL_DATA is true or AWS credentials are missing."
            )
            self.backend = "parquet"
            self._ensure_local_data_exists()
            ensure_local_data_ready(prompt_user=False)

        if self.backend == "parquet":
            self._ensure_local_data_exists()
        elif self.backend == "database":
            self._init_database()
        elif self.backend == "cloud":
            self._init_cloud_storage()
        else:  # pragma: no cover - guard for unexpected configuration
            raise ValueError(f"Unsupported data backend: {self.backend}")

    @staticmethod
    def _is_blank(value: Optional[str]) -> bool:
        """Return True when a string value is None or empty after stripping."""

        if value is None:
            return True

        if isinstance(value, str) and not value.strip():
            return True

        return False

    def _should_use_sample_backend(self) -> bool:
        """Determine whether to bypass the cloud backend and use samples instead."""

        if settings.use_local_data:
            return True

        if self._is_blank(settings.aws_access_key_id) or self._is_blank(
            settings.aws_secret_access_key
        ):
            return True

        return False

    def _ensure_local_data_exists(self):
        """Ensure local data directory exists."""
        self.data_path.mkdir(parents=True, exist_ok=True)

    def _init_database(self):
        """Prepare SQLite database configuration."""

        try:
            self._db_path = sqlite_path_from_url(settings.database_url)
        except ValueError as exc:
            raise ValueError(f"Invalid DATABASE_URL '{settings.database_url}': {exc}") from exc

        if not self._db_path.parent.exists():
            self._db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Configured SQLite database at %s", self._db_path)

    def _init_cloud_storage(self):
        """Initialize cloud storage connection."""
        if not boto3:
            raise ImportError(
                "boto3 is required for cloud data loading but is not installed. "
                "Install dependencies with `make install` after updating requirements."
            )

        if not settings.cloud_bucket_name:
            raise ValueError("CLOUD_BUCKET_NAME must be set when USE_LOCAL_DATA=false")

        session = boto3.session.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.cloud_bucket_region,
        )

        self._s3_client = session.client("s3")

    def _load_data(self) -> pd.DataFrame:
        """Load data from storage (local or cloud)."""
        cache_key = f"all_data::{self.backend}"

        if cache_key in self.cache:
            logger.debug("Returning cached data")
            return self.cache[cache_key]

        if self.backend == "parquet":
            df = self._load_local_data()
        elif self.backend == "database":
            df = self._load_database_data()
        elif self.backend == "cloud":
            df = self._load_cloud_data()
        else:  # pragma: no cover - guard for unsupported configuration
            raise ValueError(f"Unsupported data backend: {self.backend}")

        self.cache[cache_key] = df
        return df

    def _load_local_data(self) -> pd.DataFrame:
        """Load data from local parquet files"""
        parquet_files = list(self.data_path.glob("*.parquet"))

        if not parquet_files:
            logger.warning("No parquet files found in %s", self.data_path)
            ensure_local_data_ready(prompt_user=False)
            parquet_files = list(self.data_path.glob("*.parquet"))

        if not parquet_files:
            logger.error(
                "Unable to create sample data automatically. Returning empty DataFrame for safety."
            )
            return pd.DataFrame(columns=FORECAST_COLUMNS)

        dfs = []
        for file in parquet_files:
            try:
                df = pd.read_parquet(file)
                dfs.append(df)
            except Exception as e:
                logger.error(f"Error loading {file}: {e}")

        if dfs:
            return pd.concat(dfs, ignore_index=True)
        else:
            return self._create_sample_data()

    def _load_database_data(self) -> pd.DataFrame:
        """Load data from a SQLite database"""

        if not self._db_path:
            logger.error("Database path is not configured; falling back to empty DataFrame")
            return pd.DataFrame(columns=FORECAST_COLUMNS)

        if not self._db_path.exists():
            logger.warning(
                "SQLite database %s not found. Run `python scripts/load_parquet_to_db.py` "
                "or `make db-load` to populate it.",
                self._db_path,
            )
            return pd.DataFrame(columns=FORECAST_COLUMNS)

        try:
            with sqlite3.connect(self._db_path) as conn:
                df = pd.read_sql_query("SELECT * FROM forecasts", conn)
        except sqlite3.OperationalError as exc:
            logger.error("Failed to read forecasts table from %s: %s", self._db_path, exc)
            return pd.DataFrame(columns=FORECAST_COLUMNS)

        missing_columns = [col for col in FORECAST_COLUMNS if col not in df.columns]
        if missing_columns:
            logger.error(
                "Database %s is missing expected columns: %s",
                self._db_path,
                ", ".join(missing_columns),
            )
            return pd.DataFrame(columns=FORECAST_COLUMNS)

        df = df[FORECAST_COLUMNS]
        return df

    def _load_cloud_data(self) -> pd.DataFrame:
        """Load data from cloud storage"""
        if not self._s3_client:
            logger.error("S3 client is not initialized; falling back to sample data")
            return self._create_sample_data()

        bucket = settings.cloud_bucket_name
        object_keys = self._resolve_object_keys(bucket)

        if not object_keys:
            logger.warning(
                "No parquet objects found in bucket %s with prefix '%s'",
                bucket,
                settings.cloud_data_prefix,
            )
            return self._create_sample_data()

        dfs = []
        for key in object_keys:
            try:
                buffer = io.BytesIO()
                self._s3_client.download_fileobj(bucket, key, buffer)
                buffer.seek(0)
                dfs.append(pd.read_parquet(buffer))
                logger.info("Loaded %s from s3://%s/%s", key, bucket, key)
            except (ClientError, BotoCoreError) as exc:
                logger.error("Failed to download %s from bucket %s: %s", key, bucket, exc)
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.error("Failed to parse parquet %s in bucket %s: %s", key, bucket, exc)

        if not dfs:
            logger.error("Unable to load any parquet objects; returning sample data")
            return self._create_sample_data()

        return pd.concat(dfs, ignore_index=True)

    def _resolve_object_keys(self, bucket: str) -> List[str]:
        """Collect parquet object keys based on configuration."""
        if settings.cloud_data_key:
            return [settings.cloud_data_key]

        prefix = settings.cloud_data_prefix.strip("/") if settings.cloud_data_prefix else ""
        if prefix and not prefix.endswith("/"):
            prefix = f"{prefix}/"

        continuation_token = None
        keys: List[str] = []

        while True:
            try:
                list_kwargs = {"Bucket": bucket, "Prefix": prefix}
                if continuation_token:
                    list_kwargs["ContinuationToken"] = continuation_token

                response = self._s3_client.list_objects_v2(**list_kwargs)
            except (ClientError, BotoCoreError) as exc:
                logger.error("Failed to list objects in bucket %s: %s", bucket, exc)
                return []

            for obj in response.get("Contents", []):
                key = obj.get("Key")
                if key and key.endswith(".parquet"):
                    keys.append(key)

            if response.get("IsTruncated"):
                continuation_token = response.get("NextContinuationToken")
            else:
                break

        return keys

    def _create_sample_data(self) -> pd.DataFrame:
        """Create sample data for testing"""
        logger.info("Creating sample forecast data")

        df = generate_sample_forecasts()

        # Save sample data for future use
        sample_file = self.data_path / "sample_data.parquet"
        df.to_parquet(sample_file, index=False)
        logger.info(f"Sample data saved to {sample_file}")

        return df

    def get_forecasts(
        self,
        country: Optional[str] = None,
        grid_ids: Optional[List[int]] = None,
        months: Optional[List[str]] = None,
        metrics: Optional[List[MetricName]] = None,
    ) -> List[GridCellForecast]:
        """Get forecasts with optional filters"""
        df = self._load_data()

        # Apply filters
        if country:
            df = df[df["country_id"] == country]

        if grid_ids:
            df = df[df["grid_id"].isin(grid_ids)]

        if months:
            df = df[df["month"].isin(months)]

        # Convert to forecast objects
        forecasts = []
        for _, row in df.iterrows():
            forecast_dict = row.to_dict()

            # Extract metrics
            selected_metrics = [metric.value for metric in metrics] if metrics else ALL_METRIC_NAMES
            metrics_data = {
                name: forecast_dict[name] for name in selected_metrics if name in forecast_dict
            }

            forecast = GridCellForecast(
                grid_id=int(forecast_dict["grid_id"]),
                latitude=float(forecast_dict["latitude"]),
                longitude=float(forecast_dict["longitude"]),
                country_id=forecast_dict["country_id"],
                admin_1_id=forecast_dict.get("admin_1_id"),
                admin_2_id=forecast_dict.get("admin_2_id"),
                month=forecast_dict["month"],
                metrics=ForecastMetrics(**metrics_data),
            )
            forecasts.append(forecast)

        return forecasts

    def get_available_months(self) -> List[Dict[str, Any]]:
        """Get list of available forecast months"""
        df = self._load_data()

        months_data = []
        for month in df["month"].unique():
            month_df = df[df["month"] == month]
            months_data.append(
                {
                    "month": month,
                    "forecast_count": len(month_df),
                    "countries": month_df["country_id"].unique().tolist(),
                }
            )

        return sorted(months_data, key=lambda x: x["month"])

    def get_grid_cells(self, country: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of available grid cells"""
        df = self._load_data()

        if country:
            df = df[df["country_id"] == country]

        # Get unique grid cells
        grid_cells = (
            df.groupby(["grid_id", "latitude", "longitude", "country_id"]).first().reset_index()
        )

        cells_data = []
        for _, row in grid_cells.iterrows():
            cells_data.append(
                {
                    "grid_id": int(row["grid_id"]),
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "country_id": row["country_id"],
                    "admin_1_id": row.get("admin_1_id"),
                    "admin_2_id": row.get("admin_2_id"),
                }
            )

        return cells_data


# Singleton instance
data_loader = DataLoader()
