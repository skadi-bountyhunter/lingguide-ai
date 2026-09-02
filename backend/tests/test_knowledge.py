"""知识索引基础测试。"""
import asyncio
from unittest.mock import AsyncMock

import pytest

from app.services.knowledge_service import KnowledgeService


def test_split_text_is_deterministic():
    text = "灵山大佛。" * 200
    first = KnowledgeService._split_text(text)
    second = KnowledgeService._split_text(text)
    assert first == second
    assert first


def test_split_offsets_round_trip_normalized_text():
    text = "第一段\n\n\n第二段。" * 120
    normalized = KnowledgeService._normalized_text(text)
    chunks = KnowledgeService._split_text_with_offsets(text, chunk_size=40, overlap=8)
    assert chunks
    for chunk, start, end in chunks:
        assert normalized[start:end] == chunk
        assert 0 <= start < end <= len(normalized)


def test_filename_rejects_path_traversal():
    with pytest.raises(ValueError):
        KnowledgeService._safe_filename("../secret.txt")
    with pytest.raises(ValueError):
        KnowledgeService._safe_filename(r"C:\secret.txt")


def test_pdf_is_not_accepted():
    with pytest.raises(ValueError):
        asyncio.run(KnowledgeService("uploads").ingest(AsyncMock(), "x.pdf", b"%PDF"))
