"""RAG 离线评测工具的纯函数测试。"""
from tools.evaluate_rag import (
    evaluate,
    load_cases,
    ndcg_at_k,
    percentile,
    reciprocal_rank,
    resolve_relevant_chunk_ids,
    stable_chunk_key,
    validate_citations,
    check_thresholds,
)
from app.core.retrieval_types import RAGResult
from app.services.query_coordinator import build_citations


class StubService:
    def __init__(self, responses):
        self.responses = responses

    def search_with_trace(self, query, candidate_k, final_k):
        return self.responses[query]


def test_load_cases_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "cases.jsonl"
    path.write_text(
        '{"case_id":"same","query":"甲"}\n{"case_id":"same","query":"乙"}\n',
        encoding="utf-8",
    )
    try:
        load_cases(path)
    except ValueError as exc:
        assert "重复 case_id" in str(exc)
    else:
        raise AssertionError("应拒绝重复 case_id")


def test_stable_keys_map_without_random_chunk_ids():
    canonical = {
        "random-id": {
            "document_sha256": "doc-hash",
            "content_sha256": "chunk-hash",
            "chunk_index": 2,
        }
    }
    case = {
        "relevant_chunks": [{
            "document_sha256": "doc-hash",
            "chunk_sha256": "chunk-hash",
            "chunk_index": 2,
        }],
        "expected_document_ids": [],
    }
    assert stable_chunk_key("doc-hash", "chunk-hash", 2) in {
        stable_chunk_key("doc-hash", "chunk-hash", 2)
    }
    assert resolve_relevant_chunk_ids(case, canonical) == {"random-id"}


def test_ranking_metrics_handle_edges():
    assert reciprocal_rank(["x", "target"], {"target"}) == 0.5
    assert reciprocal_rank([], {"target"}) == 0.0
    assert ndcg_at_k(["target"], {"target"}) == 1.0
    assert ndcg_at_k([], set()) == 0.0
    assert percentile([], 95) == 0.0
    assert percentile([1, 2, 4, 8], 50) == 3.0
    assert percentile([1, 2, 4, 8], 95) == 7.4


def test_validate_citations_requires_canonical_content_and_locator():
    result = RAGResult(
        content="canonical evidence",
        source="doc.txt",
        score=1,
        chunk_id="chunk-1",
        char_range=(4, 22),
    )
    citations = build_citations([result])
    canonical = {
        "chunk-1": {
            "content": "canonical evidence",
            "char_start": 4,
            "char_end": 22,
        }
    }
    assert validate_citations(citations, canonical) == (1, 1, 1, 1)
    assert validate_citations(build_citations([]), canonical) == (0, 0, 0, 0)


def test_check_thresholds_reports_gate_failures():
    failures = check_thresholds(
        {"recall_at_5": 0.5, "degraded_rate": 0.02, "canonical_missing_total": 1},
        {
            "minimum": {"recall_at_5": 0.8},
            "maximum": {"degraded_rate": 0.01},
            "equals": {"canonical_missing_total": 0},
        },
    )
    assert len(failures) == 3


def test_evaluate_delegates_production_refusal_and_reports_v2_shape(tmp_path):
    from app.core.database import Base
    from app.core.database import build_runtime
    import asyncio

    database_path = tmp_path / "eval.db"
    engine, _ = build_runtime(str(database_path))

    async def create_schema():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(create_schema())
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        '{"case_id":"empty","query":"不存在","evaluation_type":"production_refusal",'
        '"qrel_status":"delegated","relevant_chunks":[],"expected_document_ids":[],'
        '"production_suite_case_id":"refuse-001","expected_route":"no_match",'
        '"expected_citation_validation":"no_evidence"}\n',
        encoding="utf-8",
    )
    report = evaluate(load_cases(dataset), StubService({}), database_path)

    assert report["suite_version"] == "rag-baseline-v2"
    assert report["query_count"] == 1
    assert report["document_recall_case_count"] == 0
    assert report["scored_query_count"] == 0
    assert report["production_refusal_cases"] == {
        "case_count": 1,
        "delegated_to": "lingguide-demo-v1",
        "cases": [{
            "case_id": "empty",
            "production_suite_case_id": "refuse-001",
            "expected_route": "no_match",
            "expected_citation_validation": "no_evidence",
        }],
    }
    assert "no_evidence_proxy" not in report
    assert report["index_version"] == "hybrid-v1"
