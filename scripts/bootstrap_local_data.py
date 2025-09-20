#!/usr/bin/env python3
"""Prompt-driven helper to prepare local forecast data for development."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running the script directly (`python scripts/bootstrap_local_data.py`)
if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.data_initializer import ensure_local_data_ready


def main() -> None:
    ensure_local_data_ready(prompt_user=True)


if __name__ == "__main__":
    main()
