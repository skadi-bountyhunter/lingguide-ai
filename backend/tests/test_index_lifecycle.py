"""隔离验证 RAG shadow 索引生命周期。"""
import sqlite3
from datetime import datetime

import pytest
from sqlalchemy import select, update

from app.models import Chunk, IndexManifest
from app.services.index_lifecycle import IndexLifecycleService
from app.services.knowledge_service import KnowledgeService


async def _ingest(runtime, content):
    service = KnowledgeService(str(runtime["chroma_path"].parent / "uploads"), rag=runtime["rag"])
    async with runtime["session_factory"]() as session:
        document = await service.ingest(session, "生命周期资料.txt", content.encode("utf-8"))
        return document.id


@pytest.mark.asyncio
async def test_shadow_build_validate_and_activate_without_deleting_old_runtime(isolated_rag_runtime):
    runtime = isolated_rag_runtime
    document_id = await _ingest(runtime, "生命周期唯一证据：五印坛城位于大佛西侧。")
    service = IndexLifecycleService(str(runtime["database_path"]), str(runtime["chroma_path"]))

    async with runtime["session_factory"]() as session:
        old_collection = runtime["rag"].collection.name
        job = await service.create_job(session, job_type="rebuild", idempotency_key="lifecycle-1")
        outcome = await service.run_job(session, job.id, owner="test-worker")
        assert outcome["state"] == "succeeded"
        manifest = await session.scalar(select(IndexManifest).where(IndexManifest.version == job.target_version))
        assert manifest and manifest.state == "validated"
        assert manifest.chunk_count == manifest.vector_count == manifest.fts_count == 1
        await service.activate(session, manifest.version)

    assert runtime["rag"].collection.name != old_collection
    assert runtime["rag"].search_with_trace("生命周期唯一证据", final_k=1).results
    assert old_collection in {item.name for item in runtime["rag"].client.list_collections()}
    with sqlite3.connect(runtime["database_path"]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM chunk_fts").fetchone()[0] == 1
    async with runtime["session_factory"]() as session:
        report = await service.reconcile(session)
    assert report["canonical_chunks"] == 1
    assert report["fts_rows"] == 1
    assert report["vector_rows"] == 1
    assert document_id


@pytest.mark.asyncio
async def test_job_idempotency_and_expired_lease_reclaim(isolated_rag_runtime):
    runtime = isolated_rag_runtime
    service = IndexLifecycleService(str(runtime["database_path"]), str(runtime["chroma_path"]))
    async with runtime["session_factory"]() as session:
        first = await service.create_job(session, job_type="rebuild", idempotency_key="lease-1")
        first_id = first.id
        duplicate = await service.create_job(session, job_type="rebuild", idempotency_key="lease-1")
        assert duplicate.id == first_id
        claimed = await service.claim_job(session, first_id, owner="worker-a")
        claimed_id = first_id
        assert claimed.attempt == 1
        with pytest.raises(ValueError):
            await service.claim_job(session, claimed_id, owner="worker-b")
        await session.execute(
            update(type(claimed)).where(type(claimed).id == claimed_id).values(
                lease_expires_at=datetime(2000, 1, 1),
            )
        )
        await session.commit()
        reclaimed = await service.claim_job(session, first_id, owner="worker-b")
        assert reclaimed.attempt == 2


@pytest.mark.asyncio
async def test_canonical_change_blocks_activation(isolated_rag_runtime):
    runtime = isolated_rag_runtime
    await _ingest(runtime, "初始生命周期证据。")
    service = IndexLifecycleService(str(runtime["database_path"]), str(runtime["chroma_path"]))
    async with runtime["session_factory"]() as session:
        job = await service.create_job(session, job_type="rebuild", idempotency_key="lifecycle-2")
        await service.run_job(session, job.id)
        row = await session.scalar(select(Chunk))
        row.content = "发生变化的 canonical 证据"
        await session.commit()
        manifest = await session.scalar(select(IndexManifest).where(IndexManifest.version == job.target_version))
        manifest.state = "validated"
        await session.commit()
        with pytest.raises(ValueError, match="canonical"):
            await service.activate(session, manifest.version)


@pytest.mark.asyncio
async def test_failed_validation_does_not_replace_active(isolated_rag_runtime):
    runtime = isolated_rag_runtime
    await _ingest(runtime, "失败保护证据。")
    service = IndexLifecycleService(str(runtime["database_path"]), str(runtime["chroma_path"]))
    async with runtime["session_factory"]() as session:
        job = await service.create_job(session, job_type="rebuild", idempotency_key="lifecycle-3")
        claimed = await service.claim_job(session, job.id)
        manifest = await session.scalar(select(IndexManifest).where(IndexManifest.version == claimed.target_version))
        manifest.chunk_count = 99
        await session.commit()
        report = await service.validate(session, manifest.version)
        assert not report["validated"]
        assert manifest.state == "failed"
        assert not await session.scalar(select(IndexManifest).where(IndexManifest.state == "active"))
