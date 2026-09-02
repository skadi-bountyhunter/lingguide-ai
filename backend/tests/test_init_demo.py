"""演示索引初始化命令的隔离验收。"""
from __future__ import annotations

import hashlib
import math

import pytest
from sqlalchemy import select

from app.core.database import Base, build_runtime
from app.models import Chunk, Document, IndexJob, IndexManifest
from tools.init_demo import initialize_demo


class _EncodedVectors:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return self._values


class FakeEmbedder:
    """确定性嵌入，避免测试依赖外部模型。"""

    def encode(self, texts, normalize_embeddings=True):
        vectors = []
        for text in texts:
            digest = hashlib.sha256(str(text).encode("utf-8")).digest()
            values = [byte / 255 for byte in digest[:8]]
            norm = math.sqrt(sum(value * value for value in values)) or 1
            vectors.append([value / norm for value in values])
        return _EncodedVectors(vectors)


@pytest.mark.asyncio
async def test_initialize_demo_builds_and_reuses_active_index(tmp_path):
    database_path = tmp_path / "demo.db"
    chroma_path = tmp_path / "chroma"
    engine, session_factory = build_runtime(str(database_path))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as db:
        document = Document(
            id="demo-document",
            filename="demo.txt",
            file_type="txt",
            status="ready",
            content_sha256="document-sha",
        )
        db.add(document)
        db.add_all(
            [
                Chunk(
                    id="demo-chunk-1",
                    document_id=document.id,
                    content="灵山大佛位于无锡。",
                    chunk_index=0,
                    content_sha256="chunk-sha-1",
                    search_text="灵山大佛位于无锡。",
                    status="ready",
                    char_start=0,
                    char_end=9,
                ),
                Chunk(
                    id="demo-chunk-2",
                    document_id=document.id,
                    content="景区提供多条游览路线。",
                    chunk_index=1,
                    content_sha256="chunk-sha-2",
                    search_text="景区提供多条游览路线。",
                    status="ready",
                    char_start=9,
                    char_end=20,
                ),
            ]
        )
        await db.commit()

    first = await initialize_demo(
        sqlite_path=str(database_path),
        chroma_path=str(chroma_path),
        embedder=FakeEmbedder(),
    )
    assert first["readiness"]["status"] == "ready"
    assert first["readiness"]["details"]["canonical_count"] == 2

    async with session_factory() as db:
        jobs_before = len((await db.execute(select(IndexJob))).scalars().all())
        manifests = (await db.execute(select(IndexManifest))).scalars().all()
        assert len(manifests) == 1
        assert manifests[0].state == "active"

    second = await initialize_demo(
        sqlite_path=str(database_path),
        chroma_path=str(chroma_path),
        embedder=FakeEmbedder(),
    )
    assert second["action"] == "already_ready"
    async with session_factory() as db:
        assert len((await db.execute(select(IndexJob))).scalars().all()) == jobs_before
        assert len((await db.execute(select(IndexManifest))).scalars().all()) == 1
    await engine.dispose()
