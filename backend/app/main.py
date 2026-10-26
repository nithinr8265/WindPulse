"""FastAPI application entry point for WindPulse Wind Forecast Evaluation API."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.clients.elexon_client import ElexonAPIError
from app.config import get_settings

settings = get_settings()

# Configure root logger
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("reint_api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    logger.info("Starting %s in %s environment", settings.APP_NAME, settings.APP_ENV)
    logger.info("Allowed CORS origins: %s", settings.cors_origins)
    logger.info("Day-ahead decision cutoff hour: D-1 at %02d:00 UTC", settings.DAY_AHEAD_DECISION_CUTOFF_HOUR)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description=(
            "REST API for a UK energy utility to evaluate Elexon BMRS day-ahead wind generation forecasts "
            "against actual generation during January 2026. Features data leakage prevention, quantitative "
            "accuracy metrics (MAE, RMSE, Bias), and configurable decision cutoffs."
        ),
        lifespan=lifespan,
    )

    # Configure CORS for future frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    app.include_router(router)

    # Custom exception handler for Elexon external API failures
    @app.exception_handler(ElexonAPIError)
    async def elexon_api_error_handler(request: Request, exc: ElexonAPIError) -> JSONResponse:
        logger.error("ElexonAPIError intercepted on %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": "error",
                "error": "ExternalServiceError",
                "message": str(exc),
                "path": request.url.path,
            },
        )

    # Global unhandled exception handler
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error": "InternalServerError",
                "message": "An unexpected server error occurred. Please check server logs.",
                "path": request.url.path,
            },
        )

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        """Root endpoint linking to API documentation."""
        return {
            "app": settings.APP_NAME,
            "version": "0.1.0",
            "documentation": "/docs",
            "openapi": "/openapi.json",
            "health": "/health",
            "evaluation_endpoint": "/api/v1/wind/evaluation?from_date=2026-01-01&to_date=2026-01-31",
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
