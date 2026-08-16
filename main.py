"""OLm-Mn-wed FastAPI application entry point.

Serves:
- ``/api/*``  : JSON API for the web UI (auth, chat, models, ...)
- ``/``       : the built Vue SPA (static files) with history-mode fallback

A second, separate ASGI app (``app.api_app``) runs on port 3001 and hosts the
OpenAI-compatible endpoints (implemented in a later stage).
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401  (register all ORM tables)
from .config import settings
from .database import Base, SessionLocal, engine
from .routers import apikeys as apikeys_router
from .routers import auth as auth_router
from .routers import chat as chat_router
from .routers import knowledge as knowledge_router
from .routers import models as models_router
from .routers import ollama as ollama_router
from .routers import personas as personas_router
from .routers import settings as settings_router
from .routers import system as system_router
from .routers import update as update_router
from .seed import seed_admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("olmwed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Startup: create tables and seed the admin user."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_admin(db)
    logger.info("%s backend v%s started.", settings.app_name, settings.version)
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

# ---------------------------------------------------------------------------
# CORS — only relevant for development (the production UI is same-origin).
# ---------------------------------------------------------------------------
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers (JSON API)
# ---------------------------------------------------------------------------
app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat_router.router, prefix="/api", tags=["chat"])
app.include_router(ollama_router.router, prefix="/api/ollama", tags=["ollama"])
app.include_router(models_router.router, prefix="/api/models", tags=["models"])
app.include_router(knowledge_router.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(apikeys_router.router, prefix="/api", tags=["api-keys"])
app.include_router(personas_router.router, prefix="/api", tags=["personas"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])
app.include_router(system_router.router, prefix="/api/system", tags=["system"])
app.include_router(update_router.router, prefix="/api/update", tags=["update"])


@app.get("/api/health", tags=["meta"])
def health():
    """Liveness probe used by the compose healthcheck."""
    return {"status": "ok", "app": settings.app_name, "version": settings.version}


# ---------------------------------------------------------------------------
# SPA static serving with history-mode fallback
# ---------------------------------------------------------------------------
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))


class SPAStaticFiles(StaticFiles):
    """StaticFiles that falls back to ``index.html`` for unknown SPA paths.

    API paths (``/api/...``) are never rewritten — they return a plain 404 so
    the frontend can surface real API errors instead of HTML.
    """

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 404 and not path.startswith("api/"):
            response = await super().get_response("index.html", scope)
        return response


if os.path.isdir(STATIC_DIR):
    app.mount("/", SPAStaticFiles(directory=STATIC_DIR, html=True), name="spa")
else:
    logger.warning("未找到前端构建产物目录 %s（开发模式下可忽略）", STATIC_DIR)
