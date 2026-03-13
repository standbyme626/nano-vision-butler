"""FastAPI application entrypoint for Vision Butler v5."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.db.session import SQLiteSessionFactory, initialize_database
from src.dependencies import api_error, api_success
from src.routes_device import router as device_router
from src.routes_memory import router as memory_router
from src.routes_ocr import router as ocr_router
from src.routes_policy import router as policy_router
from src.routes_state import router as state_router
from src.routes_telegram import router as telegram_router
from src.settings import AppConfig, load_settings


def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_db_path(repo_root: Path, app_config: AppConfig) -> Path:
    configured_path = Path(app_config.settings["database"]["path"])
    if configured_path.is_absolute():
        return configured_path
    return repo_root / configured_path


def create_app(config_dir: str | Path | None = None) -> FastAPI:
    repo_root = _resolve_repo_root()
    env_config_dir = os.getenv("VISION_BUTLER_CONFIG_DIR")
    effective_config_dir = Path(config_dir) if config_dir else Path(env_config_dir) if env_config_dir else (repo_root / "config")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app_config = load_settings(effective_config_dir)
        db_path = _resolve_db_path(repo_root, app_config)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        schema_path = repo_root / "schema.sql"
        initialize_database(db_path=db_path, schema_path=schema_path)

        session_factory = SQLiteSessionFactory(db_path)
        with session_factory.connect() as conn:
            conn.execute("SELECT 1")

        app.state.settings = app_config
        app.state.config_dir = str(effective_config_dir)
        app.state.db_path = str(db_path)
        app.state.session_factory = session_factory
        yield

    app = FastAPI(title="Vision Butler API", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=api_error("validation_error", "Request validation failed", exc.errors()),
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, exc: ValueError):
        return JSONResponse(status_code=400, content=api_error("bad_request", str(exc)))

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(status_code=exc.status_code, content=api_error("http_error", detail))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=api_error("internal_error", "Internal server error", str(exc)),
        )

    @app.get("/healthz")
    def healthz(request: Request) -> dict:
        with request.app.state.session_factory.connect() as conn:
            conn.execute("SELECT 1")
        cfg = request.app.state.settings
        return api_success(
            {
                "status": "ok",
                "app": cfg.settings["app"]["name"],
                "environment": cfg.settings["app"]["environment"],
                "database": request.app.state.db_path,
            }
        )

    app.include_router(memory_router)
    app.include_router(state_router)
    app.include_router(policy_router)
    app.include_router(device_router)
    app.include_router(ocr_router)
    app.include_router(telegram_router)

    return app


app = create_app()
