"""聊天入口在 LLM 超时时必须统一拒答且清空候选证据。"""
import asyncio

import pytest

from app.api import chat as chat_api
from app.core.retrieval_types import RAGResult
from app.services.answer_orchestrator import NO_EVIDENCE_REPLY
from app.services.query_coordinator import QueryResult


def _evidence_result() -> QueryResult:
    return QueryResult([
        RAGResult(
            content="灵山大佛是景区核心景点。",
            source="景区资料.docx",
            score=0.9,
            chunk_id="chunk-1",
            document_id="doc-1",
            content_hash="hash-1",
            fused_score=0.9,
        )
    ], route="hybrid")


@pytest.fixture
def timeout_chat(monkeypatch):
    async def retrieve_async(*_args, **_kwargs):
        return _evidence_result()

    async def get_history(*_args, **_kwargs):
        return []

    async def log(*_args, **_kwargs):
        return None

    async def slow_answer(*_args, **_kwargs):
        await asyncio.sleep(5)
        return "不应返回"

    monkeypatch.setattr(chat_api.query_coordinator, "retrieve_async", retrieve_async)
    monkeypatch.setattr(chat_api, "get_session_history", get_history)
    monkeypatch.setattr(chat_api, "log_interaction", log)
    monkeypatch.setattr(chat_api, "generate_answer", slow_answer)
    monkeypatch.setattr(chat_api.settings, "llm_timeout_seconds", 0)


@pytest.mark.asyncio
async def test_text_timeout_returns_refusal_without_citations(client, timeout_chat):
    response = await client.post("/api/chat/text", json={"query": "介绍灵山大佛"})

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == NO_EVIDENCE_REPLY
    assert body["sources"] == []
    assert body["citations"] == []
    assert body["retrieval"]["degraded"] is True
    assert "llm_deadline_exceeded" in body["retrieval"]["fallback_reason"]
    assert body["retrieval"]["citation_validation"] == "generation_timeout"


@pytest.mark.asyncio
async def test_voice_timeout_returns_refusal_without_citations(client, timeout_chat, monkeypatch):
    async def transcribe(*_args, **_kwargs):
        return "介绍灵山大佛"

    async def synthesize(*_args, **_kwargs):
        return b"audio"

    monkeypatch.setattr(chat_api, "transcribe_audio", transcribe)
    monkeypatch.setattr(chat_api, "synthesize", synthesize)
    response = await client.post(
        "/api/chat/voice",
        data={"session_id": "voice-timeout", "interests": "[]"},
        files={"audio": ("question.wav", b"audio", "audio/wav")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == NO_EVIDENCE_REPLY
    assert body["sources"] == []
    assert body["citations"] == []
    assert body["retrieval"]["degraded"] is True
    assert "llm_deadline_exceeded" in body["retrieval"]["fallback_reason"]
    assert body["retrieval"]["citation_validation"] == "generation_timeout"
