import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import forecasts, metadata
from app.core.config import settings
from app.core.settings import APP_DESCRIPTION, APP_NAME, APP_VERSION, tags_metadata
from app.models.responses import HealthResponse

logger = logging.getLogger(__name__)


def log_startup_banner() -> None:
    """Emit a simple ASCII banner announcing the service startup."""

    banner = (
        "\n"
        "RRRRR  AAAA   U   U  H   H  AAAA    ..    AAAA  PPPP   IIIII\n"
        "R   R A    A  U   U  H   H A    A  .. .. A    A P   P    I  \n"
        "RRRRR AAAAAA  U   U  HHHHH AAAAAA  .. .. AAAAAA PPPP     I  \n"
        "R  R  A    A  U   U  H   H A    A    ..  A    A P        I  \n"
        "R   R A    A   UUU   H   H A    A    ..  A    A P      IIIII\n"
        "\n"
        f"   rauha.api v{APP_VERSION} starting up\n"
        f"   Environment : {settings.environment}\n"
        f"   Data backend: {settings.data_backend}\n"
        f"   API prefix  : {settings.api_v1_prefix}\n"
    )
    logger.info("%s", banner)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    log_startup_banner()

    yield

    logger.info("Shutting down application")


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoints
@app.get("/health", tags=["health"], response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    return HealthResponse(status="healthy", version=APP_VERSION, environment=settings.environment)


@app.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness check endpoint for container orchestration"""
    # TODO: Add actual readiness checks (database connection, etc.)
    return {"status": "ready"}


# Include routers
app.include_router(forecasts.router, prefix=settings.api_v1_prefix)

app.include_router(metadata.router, prefix=settings.api_v1_prefix)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.is_development else None,
        },
    )


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "documentation": "/docs",
        "openapi": "/openapi.json",
        "endpoints": {
            "forecasts": f"{settings.api_v1_prefix}/forecasts",
            "metadata": f"{settings.api_v1_prefix}/metadata",
            "health": "/health",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
