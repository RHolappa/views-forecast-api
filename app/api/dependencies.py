
from fastapi import Header, HTTPException, status

from app.core.config import settings


async def verify_api_key(x_api_key: str | None = Header(None)) -> bool:
    """Verify API key if configured"""
    if not settings.api_key:
        # No API key configured, allow access
        return True

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return True
