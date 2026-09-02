"""隔离运行时上的 canonical、FTS5、Chroma 和引用全链路验收。"""
import sqlite3

import pytest
from sqlalchemy import select

from app.core.retrieval_types import RAGResult
from app.models import Chunk, Document
from app.services.knowledge_service import KnowledgeService
from app.services.query_coordinator import build_citations


async def _ingest(runtime, filename, content):
    service = KnowledgeService(str(runtime["chroma_path"].parent / "uploads"), rag=runtime["rag"])
    async with runtime["session_factory"]() as session:
        document = await service.ingest(session, filename, content.encode("utf-8"))
        return document.id


@pytest.mark.asyncio
async def test_isolated_ingest_hydrates_canonical_for_all_routes(isolated_rag_runtime):
    runtime = isolated_rag_runtime
    document_id = await _ingest(
        runtime,
        "同名资料.txt",
        "唯一证据：九龙灌浴每天有四场表演，上午十点和十一点半，下午两点和三点半。",
    )
    rag = runtime["rag"]

    keyword = rag.search_with_trace("九龙灌浴三点半", final_k=5)
    assert keyword.results
    assert keyword.route in {"keyword", "hybrid"}
    assert all(item.document_id == document_id for item in keyword.results)
    assert all(item.content.startswith("唯一证据：") for item in keyword.results)

    vector = rag.search_with_trace("唯一证据：九龙灌浴每天有四场表演", final_k=1)
    assert vector.results
    assert vector.results[0].content.startswith("唯一证据：")

    result = vector.results[0]
    citations = build_citations([result])
    citation = citations[0]
    assert citation.chunk_id == result.chunk_id
    assert citation.quote == result.content[:220]
    assert citation.locator["char_start"] == result.char_range[0]
    assert citation.locator["char_end"] == result.char_range[1]


@pytest.mark.asyncio
async def test_each_retrieval_route_keeps_canonical_content(isolated_rag_runtime):
    runtime = isolated_rag_runtime
    await _ingest(runtime, "路由资料.txt", "路由验收短语：五印坛城位于灵山大佛西侧。")

    rag = runtime["rag"]
    vector = rag.vector
    rag.vector = None
    keyword_result = rag.search_with_trace("路由验收短语 五印坛城", final_k=1)
    assert keyword_result.route == "keyword"
    assert keyword_result.results[0].content.startswith("路由验收短语：")

    rag.vector = vector
    rag.keyword.available = False
    vector_result = rag.search_with_trace("路由验收短语：五印坛城", final_k=1)
    assert vector_result.route == "vector"
    assert vector_result.results[0].content.startswith("路由验收短语：")


@pytest.mark.asyncio
async def test_vector_orphan_is_dropped_and_reported(isolated_rag_runtime):
    rag = isolated_rag_runtime["rag"]
    rag.vector.add_chunks(
        ["这条正文没有 canonical 记录"],
        "orphan-doc",
        [{
            "chunk_id": "orphan-chunk",
            "document_id": "orphan-doc",
            "source": "历史向量.txt",
        }],
    )

    result = rag.search_with_trace("这条正文没有 canonical 记录", final_k=5)
    assert "canonical_missing=1" in (result.fallback_reason or "")
    assert all(item.chunk_id != "orphan-chunk" for item in result.results)


@pytest.mark.asyncio
async def test_same_filename_documents_delete_independently(isolated_rag_runtime):
    runtime = isolated_rag_runtime
    first_id = await _ingest(runtime, "重复名称.txt", "甲文档独有词：紫竹林东侧。")
    second_id = await _ingest(runtime, "重复名称.txt", "乙文档独有词：白塔南侧。")
    service = KnowledgeService(str(runtime["chroma_path"].parent / "uploads"), rag=runtime["rag"])

    async with runtime["session_factory"]() as session:
        assert await service.delete(session, first_id)

    remaining = runtime["rag"].search_with_trace("乙文档独有词 白塔南侧", final_k=5)
    assert remaining.results
    assert all(item.document_id == second_id for item in remaining.results)
    assert all(item.document_id != first_id for item in remaining.results)

    with sqlite3.connect(runtime["database_path"]) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM chunk_fts WHERE document_id = ?", (first_id,)
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM chunk_fts WHERE document_id = ?", (second_id,)
        ).fetchone()[0] > 0


@pytest.mark.asyncio
async def test_canonical_chunk_offsets_round_trip(isolated_rag_runtime):
    runtime = isolated_rag_runtime
    document_id = await _ingest(runtime, "偏移.txt", "第一段。\n\n第二段包含可核验短语。\n\n第三段。")
    async with runtime["session_factory"]() as session:
        chunk = await session.scalar(select(Chunk).where(Chunk.document_id == document_id))
        document = await session.get(Document, document_id)

    assert chunk and document
    normalized = KnowledgeService._normalized_text("第一段。\n\n第二段包含可核验短语。\n\n第三段。")
    assert normalized[chunk.char_start:chunk.char_end] == chunk.content
    assert chunk.content_sha256
    assert document.status == "ready"
