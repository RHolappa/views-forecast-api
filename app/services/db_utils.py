"""Shared helpers for database-backed storage."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


def sqlite_path_from_url(database_url: str) -> Path:
    """Resolve the filesystem path from a sqlite:// URL."""

    parsed = urlparse(database_url)
    if parsed.scheme != "sqlite":
        raise ValueError("Only sqlite URLs are supported for the database backend")

    if parsed.netloc not in {"", None}:
        raise ValueError("sqlite URLs must not define a network location")

    path_str = parsed.path or ""
    if not path_str:
        raise ValueError("sqlite URL is missing a database path")

    if path_str.startswith("//"):
        path_str = path_str[1:]
    elif path_str.startswith("/"):
        path_str = path_str[1:]

    return Path(path_str).expanduser()
