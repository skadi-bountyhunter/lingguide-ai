"""灵境导游 FastAPI 应用入口。"""
from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import (
    analytics,
    auth,
    avatar,
    chat,
    dashboard,
    feedback,
    knowledge,
    notifications,
    pins,
    profile,
    rag_admin,
    routes,
    saved_routes,
    spots,
    users,
    visits,
    weather,
)
from app.config import resolve_resource_path, resolve_runtime_path, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """初始化本地数据库和公开种子数据。"""
    logger.info("灵境导游服务启动")
    from app.core.database import async_session, init_db
    from app.api.routes import seed_routes
    from app.api.spots import seed_spots

    await init_db()
    async with async_session() as session:
        await seed_spots(session)
        await seed_routes(session)
    os.makedirs(resolve_runtime_path(settings.upload_dir), exist_ok=True)
    yield
    from app.core.tools.amap_tools import close_http_client

    await close_http_client()
    logger.info("灵境导游服务关闭")


app = FastAPI(
    title="灵境导游 LingGuide",
    description="AI 数字人智慧导览系统",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.is_desktop else "/docs",
    redoc_url=None if settings.is_desktop else "/redoc",
    openapi_url=None if settings.is_desktop else "/openapi.json",
)

_origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# API 必须先注册，静态站点挂载在最后，确保 /api 永不被 history fallback 截获。
for router in (
    chat.router,
    knowledge.router,
    avatar.router,
    analytics.router,
    dashboard.router,
    auth.router,
    users.router,
    profile.router,
    feedback.router,
    notifications.router,
    spots.router,
    routes.router,
    saved_routes.router,
    pins.router,
    visits.router,
    weather.router,
    rag_admin.router,
):
    app.include_router(router)


if not settings.is_desktop:
    @app.get("/")
    async def root():
        return {"name": "灵境导游 LingGuide", "version": "1.0.0", "docs": "/docs"}


@app.get("/api/health")
async def health_check():
    """不依赖外部服务的存活检查。"""
    return {"status": "healthy", "service": "lingguide"}


def _lite_readiness(sqlite_path: str) -> tuple[dict[str, bool], dict[str, int]]:
    """检查便携版必须具备的 SQLite canonical/FTS 能力。"""
    checks = {"database": False, "canonical": False, "fts": False}
    details = {"canonical_count": 0, "fts_count": 0}
    with sqlite3.connect(sqlite_path) as connection:
        connection.execute("SELECT 1").fetchone()
        checks["database"] = True
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            )
        }
        schema_ready = {"documents", "chunks", "faqs"}.issubset(tables)
        details["faq_count"] = int(
            connection.execute(
                "SELECT COUNT(*) FROM faqs WHERE COALESCE(status, 'active') = 'active'"
            ).fetchone()[0]
        ) if schema_ready else 0
        if schema_ready:
            details["canonical_count"] = int(
                connection.execute(
                    "SELECT COUNT(*) FROM chunks WHERE COALESCE(status, 'ready') = 'ready'"
                ).fetchone()[0]
            )
        checks["canonical"] = schema_ready and details["faq_count"] > 0
        fts_schema = "chunk_fts" in tables
        if fts_schema:
            details["fts_count"] = int(
                connection.execute("SELECT COUNT(*) FROM chunk_fts").fetchone()[0]
            )
        checks["fts"] = bool(
            fts_schema
            and details["canonical_count"] == details["fts_count"]
        )
    return checks, details


@app.get("/api/readiness")
async def readiness_check():
    """便携/lite 只要求 SQLite canonical/FTS；开发模式保持严格三路检查。"""
    from app.core.database import _sqlite_path

    capabilities = {
        "runtime_mode": settings.runtime_mode,
        "rag_mode": settings.rag_mode,
        "sqlite_fts": True,
        "sqlite_fts_content": "canonical_chunks_when_present",
        "faq": True,
        "vector_search": not settings.is_lite,
        "desktop_assets": settings.is_desktop,
    }
    if settings.is_desktop or settings.is_lite:
        try:
            checks, details = _lite_readiness(_sqlite_path)
        except Exception as exc:
            logger.warning(f"readiness 检查失败: {type(exc).__name__}")
            checks = {"database": False, "canonical": False, "fts": False}
            details = {"error": type(exc).__name__}
        ready = all(checks.values())
        payload = {
            "status": "ready" if ready else "not_ready",
            "checks": checks,
            "details": details,
            "capabilities": capabilities,
        }
        if not ready:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=payload)
        return payload

    checks = {
        "database": False,
        "manifest": False,
        "fts": False,
        "vector": False,
        "counts": False,
        "ids": False,
        "fingerprint": False,
        "config": False,
    }
    details = {}
    try:
        from sqlalchemy import select
        from app.core.database import async_session
        from app.core.index_readiness import CHUNKING_CONFIG_HASH, assess_active_index
        from app.core.index_runtime import get_active_index
        from app.core.rag import rag_service
        from app.models import Chunk, Document, IndexManifest

        with sqlite3.connect(_sqlite_path) as connection:
            connection.execute("SELECT 1").fetchone()
            checks["database"] = True
        active = get_active_index(_sqlite_path)
        details.update({"index_version": active.get("version"), "manifest_id": active.get("manifest_id")})
        async with async_session() as db:
            manifest = None
            if active.get("manifest_id"):
                manifest = await db.scalar(
                    select(IndexManifest).where(IndexManifest.id == active["manifest_id"])
                )
            canonical_rows = list(
                (
                    await db.execute(
                        select(Chunk)
                        .join(Document, Document.id == Chunk.document_id)
                        .where(Chunk.status == "ready", Document.status == "ready")
                    )
                ).scalars().all()
            )
        with sqlite3.connect(_sqlite_path) as connection:
            fts_available = bool(
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (active["fts_namespace"],),
                ).fetchone()
            )
            fts_count = int(
                connection.execute(f"SELECT COUNT(*) FROM {active['fts_namespace']}").fetchone()[0]
            ) if fts_available else 0
        vector_ids = None
        if rag_service.vector:
            try:
                collection = rag_service.vector.client.get_collection(name=active["vector_collection"])
                vector_ids = [str(item) for item in (collection.get(include=[]).get("ids") or [])]
            except Exception:
                vector_ids = None
        report = assess_active_index(
            manifest,
            active,
            canonical_rows,
            fts_available=fts_available,
            fts_count=fts_count,
            vector_ids=vector_ids,
            expected_embedding_model=settings.embedding_model,
            expected_config_hash=CHUNKING_CONFIG_HASH,
        )
        checks.update(report["checks"])
        details.update(report["details"])
    except Exception as exc:
        logger.warning(f"readiness 检查失败: {type(exc).__name__}")
        details["error"] = type(exc).__name__
    ready = all(checks.values())
    payload = {
        "status": "ready" if ready else "not_ready",
        "checks": checks,
        "details": details,
        "capabilities": capabilities,
    }
    if not ready and settings.readiness_strict:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=payload)
    return payload


class HistoryStaticFiles(StaticFiles):
    """静态文件不存在时返回 SPA 入口，保留前端 history 路由。"""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (StarletteHTTPException, HTTPException) as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)


if settings.is_desktop:
    visitor_dist = Path(resolve_resource_path("web", "visitor"))
    admin_dist = Path(resolve_resource_path("web", "admin"))
    if admin_dist.is_dir():
        app.mount("/admin", HistoryStaticFiles(directory=admin_dist, html=True), name="admin-web")
    if visitor_dist.is_dir():
        app.mount("/", HistoryStaticFiles(directory=visitor_dist, html=True), name="visitor-web")
else:
    visitor_public = Path(__file__).resolve().parents[2] / "frontend-visitor" / "public" / "images"
    if visitor_public.is_dir():
        app.mount("/images", StaticFiles(directory=visitor_public), name="visitor-images")
