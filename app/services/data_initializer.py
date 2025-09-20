"""Helpers for preparing local forecast data for development."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.sample_data import write_sample_forecasts

PROMPT_TEMPLATE = "No parquet files found in {data_dir}. Generate a sample dataset now? [Y/n] "


def ensure_local_data_ready(prompt_user: bool = False) -> Optional[Path]:
    """Ensure the local data directory contains at least one parquet file."""

    data_dir = Path(settings.data_path)
    data_dir.mkdir(parents=True, exist_ok=True)

    parquet_files = list(data_dir.glob("*.parquet"))
    if parquet_files:
        return None

    if prompt_user:
        answer = input(PROMPT_TEMPLATE.format(data_dir=data_dir)).strip().lower()
        if answer not in {"", "y", "yes"}:
            print(
                "Skipping sample data creation. You can re-run `python scripts/bootstrap_local_data.py` "
                "once you have real forecasts or change DATA_PATH to another directory."
            )
            return None

    output_path = data_dir / "sample_data.parquet"
    write_sample_forecasts(output_path)
    print(f"Created sample dataset at {output_path}")
    return output_path
