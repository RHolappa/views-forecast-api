import os
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
from cachetools import TTLCache
from app.core.config import settings
from app.models.forecast import (
    GridCellForecast,
    ForecastMetrics,
    MetricName,
    ALL_METRIC_NAMES,
)

logger = logging.getLogger(__name__)


class DataLoader:
    def __init__(self):
        self.cache = TTLCache(maxsize=settings.cache_max_size, ttl=settings.cache_ttl_seconds)
        self.data_path = Path(settings.data_path)
        self._data: Optional[pd.DataFrame] = None
        
        if settings.use_local_data:
            self._ensure_local_data_exists()
        else:
            self._init_cloud_storage()
    
    def _ensure_local_data_exists(self):
        """Ensure local data directory exists"""
        self.data_path.mkdir(parents=True, exist_ok=True)
    
    def _init_cloud_storage(self):
        """Initialize cloud storage connection"""
        # TODO: Implement cloud storage connection
        # This would use boto3 for S3 or appropriate client for other cloud providers
        pass
    
    def _load_data(self) -> pd.DataFrame:
        """Load data from storage (local or cloud)"""
        cache_key = "all_data"
        
        if cache_key in self.cache:
            logger.debug("Returning cached data")
            return self.cache[cache_key]
        
        if settings.use_local_data:
            df = self._load_local_data()
        else:
            df = self._load_cloud_data()
        
        self.cache[cache_key] = df
        return df
    
    def _load_local_data(self) -> pd.DataFrame:
        """Load data from local parquet files"""
        parquet_files = list(self.data_path.glob("*.parquet"))
        
        if not parquet_files:
            logger.warning(f"No parquet files found in {self.data_path}")
            return self._create_sample_data()
        
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
    
    def _load_cloud_data(self) -> pd.DataFrame:
        """Load data from cloud storage"""
        # TODO: Implement cloud data loading
        # This would download parquet files from S3/GCS/Azure
        logger.warning("Cloud data loading not yet implemented, using sample data")
        return self._create_sample_data()
    
    def _create_sample_data(self) -> pd.DataFrame:
        """Create sample data for testing"""
        import numpy as np
        
        logger.info("Creating sample forecast data")
        
        # Create a grid of sample data
        countries = ["UGA", "KEN", "TZA"]  # Uganda, Kenya, Tanzania
        months = ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"]
        
        data = []
        grid_id = 1
        
        for country in countries:
            # Create 10 grid cells per country
            for i in range(10):
                lat = np.random.uniform(-10, 10)
                lon = np.random.uniform(20, 40)
                
                for month in months:
                    # Generate realistic-looking forecast data
                    map_value = np.random.exponential(scale=10)
                    
                    row = {
                        'grid_id': grid_id,
                        'latitude': round(lat, 4),
                        'longitude': round(lon, 4),
                        'country_id': country,
                        'admin_1_id': f"{country}_R{i//3}",
                        'admin_2_id': f"{country}_D{i}",
                        'month': month,
                        'map': map_value,
                        'ci_50_low': map_value * 0.7,
                        'ci_50_high': map_value * 1.3,
                        'ci_90_low': map_value * 0.4,
                        'ci_90_high': map_value * 2.0,
                        'ci_99_low': map_value * 0.1,
                        'ci_99_high': map_value * 3.5,
                        'prob_0': np.random.beta(5, 2),
                        'prob_1': np.random.beta(4, 3),
                        'prob_10': np.random.beta(3, 4),
                        'prob_100': np.random.beta(2, 5),
                        'prob_1000': np.random.beta(1, 6),
                        'prob_10000': np.random.beta(1, 10),
                    }
                    data.append(row)
                
                grid_id += 1
        
        df = pd.DataFrame(data)
        
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
        metrics: Optional[List[MetricName]] = None
    ) -> List[GridCellForecast]:
        """Get forecasts with optional filters"""
        df = self._load_data()
        
        # Apply filters
        if country:
            df = df[df['country_id'] == country]
        
        if grid_ids:
            df = df[df['grid_id'].isin(grid_ids)]
        
        if months:
            df = df[df['month'].isin(months)]
        
        # Convert to forecast objects
        forecasts = []
        for _, row in df.iterrows():
            forecast_dict = row.to_dict()

            # Extract metrics
            selected_metrics = [metric.value for metric in metrics] if metrics else ALL_METRIC_NAMES
            metrics_data = {
                name: forecast_dict[name]
                for name in selected_metrics
                if name in forecast_dict
            }

            forecast = GridCellForecast(
                grid_id=int(forecast_dict['grid_id']),
                latitude=float(forecast_dict['latitude']),
                longitude=float(forecast_dict['longitude']),
                country_id=forecast_dict['country_id'],
                admin_1_id=forecast_dict.get('admin_1_id'),
                admin_2_id=forecast_dict.get('admin_2_id'),
                month=forecast_dict['month'],
                metrics=ForecastMetrics(**metrics_data)
            )
            forecasts.append(forecast)
        
        return forecasts
    
    def get_available_months(self) -> List[Dict[str, Any]]:
        """Get list of available forecast months"""
        df = self._load_data()
        
        months_data = []
        for month in df['month'].unique():
            month_df = df[df['month'] == month]
            months_data.append({
                'month': month,
                'forecast_count': len(month_df),
                'countries': month_df['country_id'].unique().tolist()
            })
        
        return sorted(months_data, key=lambda x: x['month'])
    
    def get_grid_cells(self, country: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of available grid cells"""
        df = self._load_data()
        
        if country:
            df = df[df['country_id'] == country]
        
        # Get unique grid cells
        grid_cells = df.groupby(['grid_id', 'latitude', 'longitude', 'country_id']).first().reset_index()
        
        cells_data = []
        for _, row in grid_cells.iterrows():
            cells_data.append({
                'grid_id': int(row['grid_id']),
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude']),
                'country_id': row['country_id'],
                'admin_1_id': row.get('admin_1_id'),
                'admin_2_id': row.get('admin_2_id')
            })
        
        return cells_data


# Singleton instance
data_loader = DataLoader()
