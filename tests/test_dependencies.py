import pytest
from fastapi import HTTPException

from app.api.dependencies import verify_api_key
from app.core.config import settings


@pytest.fixture(autouse=True)
def restore_api_key():
    original = settings.api_key
    yield
    settings.api_key = original


@pytest.mark.asyncio
async def test_verify_api_key_allows_when_not_configured():
    settings.api_key = None
    assert await verify_api_key() is True


@pytest.mark.asyncio
async def test_verify_api_key_rejects_missing_header():
    settings.api_key = "secret"
    with pytest.raises(HTTPException) as exc:
        await verify_api_key()
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_api_key_rejects_invalid_key():
    settings.api_key = "secret"
    with pytest.raises(HTTPException):
        await verify_api_key(x_api_key="wrong")


@pytest.mark.asyncio
async def test_verify_api_key_accepts_valid_key():
    settings.api_key = "secret"
    assert await verify_api_key(x_api_key="secret") is True
