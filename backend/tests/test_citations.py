"""引用协议单元测试。"""
from app.services.query_coordinator import QueryResult
from app.core.retrieval_types import RAGResult


def test_citations_are_generated_from_evidence_and_sources_keep_order():
    result = QueryResult([
        RAGResult(content="第一条证据", source="a.txt", score=.2, chunk_id="a"),
        RAGResult(content="第二条证据", source="a.txt", score=.1, chunk_id="b"),
    ], route="hybrid")
    assert [item.id for item in result.citations] == ["C1", "C2"]
    assert result.sources == ["a.txt"]
    assert result.citations[0].quote == "第一条证据"


def test_no_evidence_has_no_citation():
    result = QueryResult([], route="no_match")
    assert result.citations == []
    assert result.sources == []
