"""RAG 管理诊断 API。"""
import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.core.index_runtime import get_active_index
from app.core.rag import SQLiteLexicalRetriever, rag_service
from app.models import Chunk, Document, IndexJob, IndexManifest, Interaction
from app.services.query_coordinator import query_coordinator
from app.services.index_lifecycle import index_lifecycle

router = APIRouter(prefix="/api/rag-admin", tags=["RAG 管理"])


class RetrievalTestRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


_RUNTIME_CHANNELS = ("structured", "fts", "bge", "weather", "llm")
_CHANNEL_FAILURE_STATUSES = {"failed", "timeout", "error", "unavailable"}


def _percentile(values: list[int], percentage: int) -> float:
    """使用线性插值计算运行耗时分位数。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentage / 100
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower), 3)


def _runtime_metric(values: list[int]) -> dict[str, float | int]:
    """构建不含原始请求内容的耗时汇总。"""
    return {
        "sample_count": len(values),
        "p50_ms": _percentile(values, 50),
        "p95_ms": _percentile(values, 95),
    }


def _ratio(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def _is_runtime_trace(value: dict) -> bool:
    """排除旧记录中的空对象，只统计实际检索轨迹。"""
    return any(key in value for key in ("latency_ms", "route", "chosen_route", "channels", "degraded"))


@router.get("/health")
async def rag_health(db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    """返回当前 active 索引的 canonical、FTS、向量和文档数量对账。"""
    from app.config import settings
    from app.core.database import _sqlite_path
    from app.core.index_readiness import CHUNKING_CONFIG_HASH, assess_active_index
    import sqlite3

    active = get_active_index(_sqlite_path)
    canonical_rows = list((await db.execute(
        select(Chunk)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.status == "ready", Document.status == "ready")
    )).scalars().all())
    documents = await db.scalar(
        select(func.count(Document.id)).where(Document.status == "ready")
    ) or 0
    manifest = await db.scalar(select(IndexManifest).where(IndexManifest.id == active.get("manifest_id")))
    lexical = SQLiteLexicalRetriever(_sqlite_path, namespace=active["fts_namespace"])
    fts_count = 0
    if lexical.available:
        with sqlite3.connect(lexical.db_path) as connection:
            fts_count = int(connection.execute(
                f"SELECT COUNT(*) FROM {active['fts_namespace']}"
            ).fetchone()[0])
    vector_ids = None
    if rag_service.vector:
        try:
            collection = rag_service.vector.client.get_collection(name=active["vector_collection"])
            vector_ids = [str(item) for item in collection.get(include=[]).get("ids") or []]
        except Exception:
            vector_ids = None
    report = assess_active_index(
        manifest,
        active,
        canonical_rows,
        fts_available=lexical.available,
        fts_count=fts_count,
        vector_ids=vector_ids,
        expected_embedding_model=settings.embedding_model,
        expected_config_hash=CHUNKING_CONFIG_HASH,
    )
    vector_count = len(vector_ids or [])
    return {
        "status": "healthy" if all(report["checks"].values()) else "degraded",
        "documents": int(documents),
        "canonical_chunks": len(canonical_rows),
        "fts_rows": fts_count,
        "vector_rows": vector_count,
        "legacy_orphan_estimate": max(0, vector_count - len(canonical_rows)),
        "index_version": active["version"],
        "manifest_id": active.get("manifest_id"),
        "fts_namespace": active["fts_namespace"],
        "vector_collection": active["vector_collection"],
        "checks": report["checks"],
        "details": report["details"],
    }


@router.get("/runtime-summary")
async def runtime_summary(db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    """聚合最近已完成交互的低敏运行指标，不返回用户原文或回答。"""
    rows = (await db.execute(
        select(Interaction)
        .where(Interaction.retrieval_json.is_not(None))
        .order_by(Interaction.created_at.desc())
        .limit(100)
    )).scalars().all()
    records: list[tuple[Interaction, dict]] = []
    for row in reversed(rows):
        try:
            retrieval = json.loads(row.retrieval_json or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(retrieval, dict) and _is_runtime_trace(retrieval):
            records.append((row, retrieval))

    total = len(records)
    total_latencies = [
        int(row.thinking_time_ms)
        for row, _ in records
        if isinstance(row.thinking_time_ms, int) and row.thinking_time_ms >= 0
    ]
    retrieval_latencies = [
        int(retrieval["latency_ms"])
        for _, retrieval in records
        if isinstance(retrieval.get("latency_ms"), (int, float)) and retrieval["latency_ms"] >= 0
    ]
    degraded_count = sum(bool(retrieval.get("degraded")) for _, retrieval in records)
    channel_latencies = {name: [] for name in _RUNTIME_CHANNELS}
    abnormal_request_count = 0

    for _, retrieval in records:
        channels = retrieval.get("channels")
        request_abnormal = False
        if not isinstance(channels, dict):
            continue
        for name in _RUNTIME_CHANNELS:
            channel = channels.get(name)
            if not isinstance(channel, dict):
                continue
            status = str(channel.get("status") or "")
            latency = channel.get("latency_ms")
            if status != "skipped" and isinstance(latency, (int, float)) and latency >= 0:
                channel_latencies[name].append(int(latency))
            if status in _CHANNEL_FAILURE_STATUSES:
                request_abnormal = True
        abnormal_request_count += request_abnormal

    created_at = [row.created_at.isoformat() for row, _ in records if row.created_at]
    return {
        "window_size": 100,
        "request_count": total,
        "first_recorded_at": created_at[0] if created_at else None,
        "last_recorded_at": created_at[-1] if created_at else None,
        "end_to_end": _runtime_metric(total_latencies),
        "retrieval": _runtime_metric(retrieval_latencies),
        "degraded": {"count": degraded_count, "rate": _ratio(degraded_count, total)},
        "channel_abnormal": {
            "count": abnormal_request_count,
            "rate": _ratio(abnormal_request_count, total),
        },
        "channels": {
            name: {
                "sample_count": len(latencies),
                "avg_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else None,
            }
            for name, latencies in channel_latencies.items()
        },
    }


@router.post("/retrieval-test")
async def retrieval_test(req: RetrievalTestRequest, _admin=Depends(require_admin)):
    """管理员查看一次完整的过滤后检索证据，不执行生成。"""
    result = await query_coordinator.retrieve_async(req.query, top_k=req.top_k)
    return result.as_dict() | {"results": [item.to_dict() for item in result.results]}


@router.get("/chunks/{chunk_id}")
async def chunk_detail(chunk_id: str, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    chunk = await db.get(Chunk, chunk_id)
    if not chunk:
        raise HTTPException(404, "分块不存在")
    return {
        "id": chunk.id,
        "document_id": chunk.document_id,
        "content": chunk.content,
        "chunk_index": chunk.chunk_index,
        "content_sha256": chunk.content_sha256,
        "index_version": chunk.index_version,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
        "status": chunk.status,
    }


class JobRequest(BaseModel):
    job_type: str = Field(default="rebuild", min_length=1, max_length=50)
    idempotency_key: str = Field(min_length=1, max_length=255)


@router.post("/jobs")
async def create_job(req: JobRequest, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    job = await index_lifecycle.create_job(db, job_type=req.job_type, idempotency_key=req.idempotency_key)
    return {"id": job.id, "target_version": job.target_version, "state": job.state, "idempotency_key": job.idempotency_key}


@router.post("/jobs/{job_id}/run")
async def run_job(job_id: str, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    try:
        return await index_lifecycle.run_job(db, job_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, "索引任务执行失败，请查看任务状态") from exc


@router.get("/jobs")
async def list_jobs(db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    rows = (await db.execute(select(IndexJob).order_by(IndexJob.created_at.desc()).limit(100))).scalars().all()
    return [{
        "id": row.id,
        "job_type": row.job_type,
        "target_version": row.target_version,
        "state": row.state,
        "attempt": row.attempt,
        "error_message": row.error_message or "",
        "created_at": row.created_at.isoformat() if row.created_at else "",
    } for row in rows]


@router.post("/manifests/{version}/validate")
async def validate_manifest(version: str, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    return await index_lifecycle.validate(db, version)


@router.post("/manifests/{version}/activate")
async def activate_manifest(version: str, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    try:
        manifest = await index_lifecycle.activate(db, version)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"id": manifest.id, "version": manifest.version, "state": manifest.state}


@router.get("/reconcile")
async def reconcile_index(db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    return await index_lifecycle.reconcile(db)


@router.get("/manifests")
async def list_manifests(db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    rows = (await db.execute(select(IndexManifest).order_by(IndexManifest.created_at.desc()).limit(50))).scalars().all()
    return [{
        "id": row.id,
        "version": row.version,
        "state": row.state,
        "vector_collection": row.vector_collection,
        "fts_namespace": row.fts_namespace,
        "chunk_count": row.chunk_count,
        "vector_count": row.vector_count,
        "fts_count": row.fts_count,
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "activated_at": row.activated_at.isoformat() if row.activated_at else None,
    } for row in rows]


def _trace_text_summary(value: str | None) -> dict[str, int | str]:
    """为管理诊断提供低敏摘要，不返回完整用户原文。"""
    text = value or ""
    return {
        "length": len(text),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "",
    }


@router.get("/traces/{trace_id}")
async def trace_detail(trace_id: str, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    row = await db.scalar(select(Interaction).where(Interaction.trace_id == trace_id))
    if not row:
        raise HTTPException(404, "检索轨迹不存在")
    import json
    try:
        citations = json.loads(row.citations_json or "[]")
    except (TypeError, json.JSONDecodeError):
        citations = []
    try:
        retrieval = json.loads(row.retrieval_json or "{}")
    except (TypeError, json.JSONDecodeError):
        retrieval = {}
    return {
        "trace_id": row.trace_id,
        "session_id": _trace_text_summary(row.session_id),
        "query": _trace_text_summary(row.query_text),
        "response": _trace_text_summary(row.response_text),
        "citations": citations,
        "retrieval": retrieval,
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }
