"""证据过滤和答案 Citation ID 校验测试。"""
import pytest

from app.core.retrieval_types import RAGResult
from app.services.query_coordinator import (
    QueryCoordinator,
    QueryResult,
    extract_citation_ids,
    filter_evidence,
    validate_answer_citations,
    faq_to_query_result,
    match_faq,
    weather_to_query_result,
)




def test_filter_evidence_rejects_missing_canonical_identity():
    accepted, reasons = filter_evidence([
        RAGResult(content="弱证据", source="x", score=0.1, chunk_id="", document_id=""),
    ])
    assert accepted == []
    assert any("missing_canonical_id" in reason for reason in reasons)


def test_filter_evidence_keeps_relevant_canonical_result_and_assigns_confidence():
    result = RAGResult(
        content="规范证据",
        source="x",
        score=0.1,
        chunk_id="chunk-1",
        document_id="doc-1",
        content_hash="hash",
        fused_score=1 / 61,
        vector_score=0.8,
    )
    accepted, reasons = filter_evidence([result])
    assert accepted == [result]
    assert not reasons
    assert result.confidence is not None


def test_filter_evidence_does_not_treat_canonical_identity_as_relevance():
    result = RAGResult(
        content="不相关但可回查的证据",
        source="x",
        score=0.01,
        chunk_id="chunk-1",
        document_id="doc-1",
        content_hash="hash",
        fused_score=1 / 61,
    )
    accepted, reasons = filter_evidence([result])
    assert accepted == []
    assert reasons == ["chunk-1:confidence_0.0492"]


def test_faq_uses_unified_canonical_identity():
    faq = {
        "id": 7,
        "answer": "五印坛城属于藏传佛教风格建筑。",
    }
    result = faq_to_query_result(faq)
    assert result.route == "faq"
    assert result.citations[0].document_id == "faq:7"
    assert result.citations[0].chunk_id == "faq:7"
    assert result.citations[0].evidence_type == "faq"


def test_faq_route_match_is_shared_by_coordinator():
    assert match_faq("灵山大佛有多高？")["answer"].startswith("灵山大佛高达88米")
    assert match_faq("规划一条灵山路线") is None


@pytest.mark.asyncio
async def test_explicitly_unavailable_request_skips_all_retrieval():
    result = await QueryCoordinator().retrieve_async("请告诉我资料库中没有的实时客流数字。")
    assert result.route == "no_match"
    assert result.citations == []
    assert result.trace.citation_validation == "no_evidence"
    assert result.trace.fallback_reason == "unsupported_or_unavailable_request"


def test_weather_evidence_keeps_tool_metadata_and_expiry():
    result = weather_to_query_result({
        "id": "tool:weather-1",
        "content": "无锡当前天气：晴，气温 25°C。",
        "source": {"title": "无锡"},
        "confidence": 0.95,
        "quality_reason": "fresh_amap_weather",
        "provider": "amap",
        "tool_call_id": "tool-1",
        "as_of": "2026-07-18T00:00:00+00:00",
        "expires_at": "2099-07-18T00:00:00+00:00",
        "status": "ready",
    })
    citation = result.citations[0]
    assert citation.provider == "amap"
    assert citation.tool_call_id == "tool-1"
    assert citation.expires_at.startswith("2099-")
    assert result.trace.index_version == "weather-live"


def test_citation_ids_reject_unknown_ids():
    result = QueryResult([
        RAGResult(content="证据", source="doc", score=1, chunk_id="c", document_id="d", content_hash="h", fused_score=1),
    ])
    assert extract_citation_ids("依据【C1】和[C9]") == ["C1", "C9"]
    assert validate_answer_citations("依据【C1】和[C9]", result.citations) == (["C1"], ["C9"])
