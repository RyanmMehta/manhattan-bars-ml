import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import errors
from .config import Settings, get_settings
from .context import Ctx
from .db import make_database
from .engine import get_engine
from .genres import load_genres
from .logging import setup_logging
from .repo.sources import Sources
from .repo.venues import load_catalog
from .routers import auth, feedback, health, heatmap, owner, recommend, reports, scouts, venues
from .simdb import read_schema, resolve_sim_path

log = logging.getLogger("app")


def build_ctx(settings: Settings) -> Ctx:
    sim_path, problems = resolve_sim_path(settings)
    db = make_database(settings, sim_path)
    if sim_path:
        schema = read_schema(sim_path)
    elif not settings.is_sqlite and db.sim_available:
        from sqlalchemy import inspect

        insp = inspect(db.engine)
        schema = {
            t: {c["name"] for c in insp.get_columns(t)}
            for t in insp.get_table_names()
            if t.startswith("syn_")
        }
    else:
        schema = {}
    src = Sources(settings.include_synthetic, db.sim_prefix, schema)
    catalog = load_catalog(
        settings.launch_venues_full_csv, settings.launch_venues_csv, settings.public_db_path
    )
    return Ctx(
        settings=settings,
        db=db,
        src=src,
        engine=get_engine(settings.recs_mode),
        catalog=catalog,
        genres=load_genres(settings.genres_json),
        sim_problems=problems,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)
    app = FastAPI(
        title="Nightlife Autopilot API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    app.state.ctx = build_ctx(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Data", "X-Total-Count"],
    )
    errors.install(app)

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        ctx = request.app.state.ctx
        log.info(
            "request",
            extra={
                "fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": round((time.perf_counter() - t0) * 1000, 1),
                    "engine": getattr(ctx.engine, "last_served", ctx.engine_label),
                }
            },
        )
        return response

    for r in (health, venues, heatmap, auth, reports, scouts, recommend, owner, feedback):
        app.include_router(r.router)
    log.info(
        "startup",
        extra={
            "fields": {
                "recs": app.state.ctx.engine_label,
                "sim": app.state.ctx.db.sim_path,
                "catalog": app.state.ctx.catalog.source,
                "include_synthetic": settings.include_synthetic,
            }
        },
    )
    return app


_app: FastAPI | None = None


def __getattr__(name: str) -> FastAPI:
    """`uvicorn app.main:app` builds the app on first access, so importing is side-effect free."""
    global _app
    if name == "app":
        if _app is None:
            _app = create_app()
        return _app
    raise AttributeError(name)
