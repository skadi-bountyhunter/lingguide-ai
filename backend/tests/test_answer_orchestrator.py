"""最终回答与 Citation 拒答语义回归。"""
import pytest

from app.core.llm import LLMGenerationError
from app.core.retrieval_types import RAGResult
from app.services import answer_orchestrator
from app.services.answer_orchestrator import NO_EVIDENCE_REPLY, generate_answer
from app.services.query_coordinator import QueryResult


def evidence_result() -> QueryResult:
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


@pytest.mark.asyncio
async def test_no_evidence_refusal_does_not_call_llm(monkeypatch):
    async def unexpected_llm(*_args, **_kwargs):
        raise AssertionError("无证据时不得调用 LLM")
        yield ""

    monkeypatch.setattr(answer_orchestrator, "generate_response", unexpected_llm)
    result = QueryResult([], route="no_match")

    assert await generate_answer("资料库外问题", result) == NO_EVIDENCE_REPLY
    assert result.citations == []
    assert result.results == []
    assert result.trace.citation_validation == "no_evidence"


@pytest.mark.asyncio
async def test_llm_failure_refusal_clears_candidate_citations(monkeypatch):
    async def failed_llm(*_args, **_kwargs):
        raise LLMGenerationError("LLM connection_error", category="connection_error")
        yield ""

    monkeypatch.setattr(answer_orchestrator, "generate_response", failed_llm)
    result = evidence_result()

    assert await generate_answer("介绍灵山大佛", result) == NO_EVIDENCE_REPLY
    assert result.citations == []
    assert result.results == []
    assert result.trace.citation_validation == "generation_failed"
    assert "llm_connection_error" in (result.trace.fallback_reason or "")


@pytest.mark.asyncio
async def test_unknown_only_citation_refuses_without_candidates(monkeypatch):
    async def reply_with_unknown(*_args, **_kwargs):
        yield "这是回答【C99】"

    monkeypatch.setattr(answer_orchestrator, "generate_response", reply_with_unknown)
    result = evidence_result()

    assert await generate_answer("介绍灵山大佛", result) == NO_EVIDENCE_REPLY
    assert result.citations == []
    assert result.results == []
    assert result.trace.citation_validation == "invalid_unknown_id"


@pytest.mark.asyncio
async def test_answer_without_citation_attaches_first_evidence(monkeypatch):
    async def plain_reply(*_args, **_kwargs):
        yield "灵山大佛是景区核心景点。"

    monkeypatch.setattr(answer_orchestrator, "generate_response", plain_reply)
    result = evidence_result()

    answer = await generate_answer("介绍灵山大佛", result)
    assert answer.endswith("【C1】")
    assert result.trace.answer_citation_ids == ["C1"]
    assert result.trace.citation_validation == "server_attached"
    assert len(result.citations) == 1
