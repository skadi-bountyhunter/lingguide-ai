"""验证 active manifest 与增量知识摄取的一致性。"""
from __future__ import annotations

from sqlalchemy import select

import pytest

from app.core.index_readiness import assess_active_index
from app.core.index_runtime import get_active_index
from app.models import Chunk, Document, IndexManifest
from app.services.index_lifecycle import IndexLifecycleService
from app.services.knowledge_service import KnowledgeService


async def _activate(runtime, key: str = "active-consistency"):
    seed_service = KnowledgeService(
        str(runtime["chroma_path"].parent / "uploads"),
        rag=runtime["rag"],
        allow_unmanaged_index=True,
    )
    async with runtime["session_factory"]() as session:
        await seed_service.ingest(session, "seed.txt", b"active manifest seed")
        lifecycle = IndexLifecycleService(
            str(runtime["database_path"]),
            str(runtime["chroma_path"]),
            embedder=runtime["rag"].vector._embedder,
        )
        job = await lifecycle.create_job(session, job_type="rebuild", idempotency_key=key)
        await lifecycle.run_job(session, job.id, owner="test")
        manifest = await session.scalar(
            select(IndexManifest).where(IndexManifest.version == job.target_version)
        )
        await lifecycle.activate(session, manifest.version)
    service = KnowledgeService(
        str(runtime["chroma_path"].parent / "uploads"),
        rag=runtime["rag"],
        index_lifecycle=lifecycle,
    )
    return service, lifecycle


async def _assert_ready(runtime, lifecycle):
    active = get_active_index(str(runtime["database_path"]))
    async with runtime["session_factory"]() as session:
        manifest = await session.scalar(
            select(IndexManifest).where(IndexManifest.id == active["manifest_id"])
        )
        rows = (
            await session.execute(
                select(Chunk)
                .join(Document, Document.id == Chunk.document_id)
                .where(Chunk.status == "ready", Document.status == "ready")
            )
        ).scalars().all()
    fts_count = lifecycle._fts_count(manifest.fts_namespace)
    vector_ids = lifecycle._vector_ids(manifest)
    report = assess_active_index(
        manifest,
        active,
        list(rows),
        fts_available=True,
        fts_count=fts_count,
        vector_ids=vector_ids,
        expected_embedding_model=manifest.embedding_model,
        expected_config_hash=manifest.config_hash,
    )
    assert all(report["checks"].values()), report
    return manifest


@pytest.mark.asyncio
async def test_upload_and_delete_refresh_active_manifest(isolated_rag_runtime):
    runtime = isolated_rag_runtime
    service, lifecycle = await _activate(runtime)

    async with runtime["session_factory"]() as session:
        document = await service.ingest(
            session,
            "增量.txt",
            "增量证据：梵宫位于灵山胜境。".encode("utf-8"),
        )
    manifest = await _assert_ready(runtime, lifecycle)
    assert manifest.state == "active"
    assert manifest.chunk_count == manifest.fts_count == manifest.vector_count == 2

    async with runtime["session_factory"]() as session:
        assert await service.delete(session, document.id)
    manifest = await _assert_ready(runtime, lifecycle)
    assert manifest.chunk_count == manifest.fts_count == manifest.vector_count == 1


@pytest.mark.asyncio
async def test_failed_active_write_keeps_manifest_and_cleans_index(isolated_rag_runtime, monkeypatch):
    runtime = isolated_rag_runtime
    service, lifecycle = await _activate(runtime, "active-failure")
    before = await _assert_ready(runtime, lifecycle)

    def fail_add(*args, **kwargs):
        raise RuntimeError("simulated index failure")

    monkeypatch.setattr(runtime["rag"], "add_chunks", fail_add)
    async with runtime["session_factory"]() as session:
        with pytest.raises(RuntimeError, match="simulated"):
            await service.ingest(
                session,
                "失败.txt",
                "失败写入证据".encode("utf-8"),
            )
        document = await session.scalar(select(Document).where(Document.filename == "失败.txt"))
        assert document and document.status == "failed"

    after = await _assert_ready(runtime, lifecycle)
    assert after.content_hash == before.content_hash
    assert after.chunk_count == before.chunk_count
    assert all(
        item.document_id != document.id
        for item in runtime["rag"].search_with_trace("失败写入证据", final_k=5).results
    )
