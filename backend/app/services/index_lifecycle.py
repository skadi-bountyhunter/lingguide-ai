"""RAG shadow 索引生命周期：构建、校验、激活和一次性任务领取。"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import resolve_runtime_path, settings
from app.core.index_readiness import (
    CHUNKING_CONFIG_HASH,
    assess_active_index,
    canonical_fingerprint,
)
from app.core.rag import HybridRAGService
from app.models import Chunk, Document, IndexJob, IndexManifest


MAX_ATTEMPTS = 3
LEASE_SECONDS = 300
_CHUNKING_CONFIG_HASH = CHUNKING_CONFIG_HASH


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _version(prefix: str = "shadow") -> str:
    return f"{prefix}-{_now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"


def _fingerprint(rows: list[Chunk]) -> str:
    return canonical_fingerprint(rows)


class IndexLifecycleService:
    """只操作独立 shadow namespace，失败时不触碰现有 active 索引。"""

    def __init__(self, sqlite_path: str | None = None, chroma_path: str | None = None, embedder=None):
        self.sqlite_path = resolve_runtime_path(sqlite_path or settings.sqlite_path)
        self.chroma_path = resolve_runtime_path(chroma_path or settings.chroma_path)
        self.embedder = embedder

    async def create_job(self, db: AsyncSession, *, job_type: str, idempotency_key: str) -> IndexJob:
        existing = await db.scalar(select(IndexJob).where(IndexJob.idempotency_key == idempotency_key))
        if existing:
            return existing
        version = _version()
        manifest = IndexManifest(
            id=uuid.uuid4().hex,
            version=version,
            state="building",
            vector_collection=f"lingguide_knowledge__{version.replace('-', '_')}",
            fts_namespace=f"chunk_fts__{version.replace('-', '_')}",
            embedding_model=settings.embedding_model,
            config_hash=_CHUNKING_CONFIG_HASH,
        )
        db.add(manifest)
        await db.flush()
        job = IndexJob(
            id=uuid.uuid4().hex,
            idempotency_key=idempotency_key,
            job_type=job_type,
            target_version=version,
            state="queued",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    async def claim_job(self, db: AsyncSession, job_id: str, *, owner: str | None = None) -> IndexJob:
        """原子领取 queued/失败重试任务；未过期租约不可被第二个 worker 抢走。"""
        now = _now()
        owner = owner or f"manual-{uuid.uuid4().hex[:8]}"
        lease_until = now + timedelta(seconds=LEASE_SECONDS)
        result = await db.execute(
            update(IndexJob)
            .where(
                IndexJob.id == job_id,
                IndexJob.attempt < MAX_ATTEMPTS,
                (IndexJob.state.in_(["queued", "failed"]))
                | ((IndexJob.state == "running") & (IndexJob.lease_expires_at < now)),
            )
            .values(
                state="running",
                lease_owner=owner,
                lease_expires_at=lease_until,
                attempt=IndexJob.attempt + 1,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            await db.rollback()
            raise ValueError("任务不存在、已被领取或已达到最大重试次数")
        await db.commit()
        job = await db.get(IndexJob, job_id)
        if not job:
            raise ValueError("索引任务不存在")
        return job

    async def _canonical_rows(self, db: AsyncSession) -> list[Chunk]:
        rows = (
            await db.execute(
                select(Chunk)
                .join(Document, Document.id == Chunk.document_id)
                .where(Chunk.status == "ready", Document.status == "ready")
                .order_by(Chunk.document_id, Chunk.chunk_index, Chunk.id)
            )
        ).scalars().all()
        return list(rows)

    def _build_writer(self, manifest: IndexManifest) -> HybridRAGService:
        writer = HybridRAGService(
            sqlite_path=self.sqlite_path,
            chroma_path=self.chroma_path,
            vector_collection=manifest.vector_collection,
            fts_namespace=manifest.fts_namespace,
            embedder=self.embedder,
        )
        # 目标 FTS 表是显式创建的，绝不读取或改变 active namespace。
        writer.keyword._ensure_schema()
        return writer

    async def run_job(self, db: AsyncSession, job_id: str, *, owner: str | None = None) -> dict[str, Any]:
        job = await self.claim_job(db, job_id, owner=owner)
        manifest = await db.scalar(select(IndexManifest).where(IndexManifest.version == job.target_version))
        if not manifest:
            await self._mark_failed(db, job, None, "manifest_missing")
            raise ValueError("索引 manifest 不存在")
        manifest.state = "building"
        await db.commit()
        try:
            rows = await self._canonical_rows(db)
            writer = self._build_writer(manifest)
            by_document: dict[str, list[Chunk]] = {}
            for row in rows:
                by_document.setdefault(str(row.document_id), []).append(row)
            for document_id, document_rows in by_document.items():
                writer.add_chunks(
                    [row.content for row in document_rows],
                    document_id,
                    [
                        {
                            "chunk_id": row.id,
                            "document_id": document_id,
                            "source": "",
                            "search_text": row.search_text or row.content,
                            "content_hash": row.content_sha256,
                            "char_start": row.char_start,
                            "char_end": row.char_end,
                            "index_version": row.index_version or job.target_version,
                        }
                        for row in document_rows
                    ],
                )
            manifest.chunk_count = len(rows)
            manifest.vector_count = writer.chunk_count
            manifest.fts_count = self._fts_count(manifest.fts_namespace)
            manifest.content_hash = _fingerprint(rows)
            manifest.state = "building"
            await db.commit()
            report = await self.validate(db, manifest.version)
            if not report["validated"]:
                await self._mark_failed(db, job, manifest, "validation_failed")
                return {"job_id": job.id, "state": job.state, "report": report}
            job.state = "succeeded"
            job.lease_owner = None
            job.lease_expires_at = None
            job.error_message = ""
            await db.commit()
            return {"job_id": job.id, "state": job.state, "report": report}
        except Exception as exc:
            await self._mark_failed(db, job, manifest, type(exc).__name__)
            raise

    async def _mark_failed(
        self,
        db: AsyncSession,
        job: IndexJob,
        manifest: IndexManifest | None,
        reason: str,
    ) -> None:
        job.state = "failed"
        job.error_message = str(reason)[:500]
        job.lease_owner = None
        job.lease_expires_at = None
        if manifest and manifest.state != "active":
            manifest.state = "failed"
        await db.commit()

    def _fts_count(self, namespace: str) -> int:
        db_path = self.sqlite_path
        with sqlite3.connect(db_path) as connection:
            row = connection.execute(f"SELECT COUNT(*) FROM {namespace}").fetchone()
        return int(row[0] or 0)

    def _vector_ids(self, manifest: IndexManifest) -> list[str]:
        from chromadb.config import Settings as ChromaSettings
        import chromadb

        client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collection = client.get_collection(name=manifest.vector_collection)
        return [str(item) for item in (collection.get(include=[]).get("ids") or [])]

    async def validate(self, db: AsyncSession, version: str) -> dict[str, Any]:
        manifest = await db.scalar(select(IndexManifest).where(IndexManifest.version == version))
        if not manifest:
            raise ValueError("索引 manifest 不存在")
        rows = await self._canonical_rows(db)
        canonical_count = len(rows)
        canonical_hash = _fingerprint(rows)
        reasons: list[str] = []
        fts_count = 0
        vector_count = 0
        try:
            fts_count = self._fts_count(manifest.fts_namespace)
        except sqlite3.Error:
            reasons.append("fts_namespace_missing")
        try:
            vector_ids = self._vector_ids(manifest)
            vector_count = len(vector_ids)
        except Exception:
            vector_ids = []
            reasons.append("vector_collection_missing")
        if not canonical_count:
            reasons.append("canonical_empty")
        if fts_count != canonical_count:
            reasons.append("fts_count_mismatch")
        if vector_count != canonical_count:
            reasons.append("vector_count_mismatch")
        if manifest.content_hash and manifest.content_hash != canonical_hash:
            reasons.append("canonical_changed")
        if manifest.chunk_count != canonical_count:
            reasons.append("chunk_count_mismatch")
        if manifest.content_hash and vector_ids:
            canonical_ids = {row.id for row in rows}
            if set(vector_ids) != canonical_ids:
                reasons.append("vector_ids_mismatch")
        manifest.chunk_count = canonical_count
        manifest.vector_count = vector_count
        manifest.fts_count = fts_count
        if not reasons:
            manifest.content_hash = canonical_hash
            manifest.state = "validated"
        else:
            manifest.state = "failed"
        await db.commit()
        return {
            "version": version,
            "canonical_chunks": canonical_count,
            "vector_count": vector_count,
            "fts_count": fts_count,
            "vector_collection": manifest.vector_collection,
            "fts_namespace": manifest.fts_namespace,
            "validated": not reasons,
            "reasons": reasons,
        }

    async def activate(self, db: AsyncSession, version: str) -> IndexManifest:
        manifest = await db.scalar(select(IndexManifest).where(IndexManifest.version == version))
        if not manifest or manifest.state != "validated":
            raise ValueError("索引未通过校验，禁止激活")
        rows = await self._canonical_rows(db)
        if manifest.content_hash != _fingerprint(rows):
            manifest.state = "failed"
            await db.commit()
            raise ValueError("canonical 数据已变化，禁止激活")
        await db.execute(
            update(IndexManifest)
            .where(IndexManifest.state == "active")
            .values(state="retired", retired_at=_now())
        )
        manifest.state = "active"
        manifest.activated_at = _now()
        await db.commit()
        await db.refresh(manifest)
        return manifest

    async def refresh_active_manifest(self, db: AsyncSession) -> dict[str, Any]:
        """刷新 active manifest 的物理索引快照，保持 active 状态不变。"""
        from app.core.index_runtime import get_active_index

        active = get_active_index(self.sqlite_path)
        if not active.get("manifest_id"):
            raise ValueError("active manifest 不存在，请先完成 shadow build、validate 和 activate")

        manifest = await db.scalar(
            select(IndexManifest).where(
                IndexManifest.id == active["manifest_id"],
                IndexManifest.state == "active",
            )
        )
        if not manifest:
            raise ValueError("active manifest 不存在或状态不是 active")

        rows = await self._canonical_rows(db)
        fts_count = 0
        fts_available = False
        try:
            fts_count = self._fts_count(manifest.fts_namespace)
            fts_available = True
        except sqlite3.Error:
            pass

        vector_ids: list[str] | None
        try:
            vector_ids = self._vector_ids(manifest)
        except Exception:
            vector_ids = None

        report = assess_active_index(
            manifest,
            active,
            rows,
            fts_available=fts_available,
            fts_count=fts_count,
            vector_ids=vector_ids,
            expected_embedding_model=settings.embedding_model,
            expected_config_hash=_CHUNKING_CONFIG_HASH,
            check_fingerprint=False,
        )
        if not all(report["checks"].values()):
            raise ValueError(f"active 索引对账失败: {','.join(name for name, ok in report['checks'].items() if not ok)}")

        manifest.content_hash = report["details"]["canonical_fingerprint"]
        manifest.chunk_count = report["details"]["canonical_count"]
        manifest.fts_count = report["details"]["fts_count"]
        manifest.vector_count = report["details"]["vector_count"]
        await db.commit()
        return {
            "manifest_id": manifest.id,
            "version": manifest.version,
            "state": manifest.state,
            **report["details"],
        }

    async def reconcile(self, db: AsyncSession) -> dict[str, Any]:
        rows = await self._canonical_rows(db)
        from app.core.index_runtime import get_active_index

        active = get_active_index(self.sqlite_path)
        fts_count = 0
        try:
            fts_count = self._fts_count(active["fts_namespace"])
        except sqlite3.Error:
            pass

        vector_count = 0
        manifest = None
        if active.get("manifest_id"):
            manifest = await db.scalar(
                select(IndexManifest).where(IndexManifest.id == active["manifest_id"])
            )
        if manifest:
            try:
                vector_count = len(self._vector_ids(manifest))
            except Exception:
                pass
        return {
            "canonical_chunks": len(rows),
            "fts_rows": fts_count,
            "vector_rows": vector_count,
            "vector_difference": vector_count - len(rows),
            "index_version": active["version"],
            "dry_run": True,
            "action": "仅报告，不删除任何索引记录",
        }


index_lifecycle = IndexLifecycleService()
