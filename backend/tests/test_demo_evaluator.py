"""竞赛演示最终回答评测器测试。"""
import pytest

from app.core.retrieval_types import RAGResult
from app.services.answer_orchestrator import NO_EVIDENCE_REPLY
from app.services.query_coordinator import QueryResult
from tools.evaluate_demo import evaluate_demo


class StubCoordinator:
    def __init__(self, result):
        self.result = result

    async def retrieve_async(self, *_args, **_kwargs):
        return self.result


@pytest.mark.asyncio
async def test_demo_evaluator_counts_only_real_refusal_cases():
    no_evidence = QueryResult([], route="no_match")
    report = await evaluate_demo(
        [
            {
                "case_id": "negative",
                "query": "不存在",
                "expected_routes": ["no_match"],
                "should_refuse": True,
            },
        ],
        StubCoordinator(no_evidence),
    )
    assert report["refusal_accuracy"] == 1.0
    assert report["grounded_answer_accuracy"] is None
    assert report["route_accuracy"] == 1.0


@pytest.mark.asyncio
async def test_demo_evaluator_checks_grounded_route_and_citation():
    result = QueryResult([
        RAGResult(
            content="灵山大佛是核心景点。",
            source="资料.docx",
            score=1,
            chunk_id="chunk-1",
            document_id="doc-1",
            content_hash="hash",
            char_range=(0, 10),
            fused_score=1,
        )
    ], route="hybrid")

    async def answer(*_args, **_kwargs):
        return "灵山大佛是核心景点【C1】"

    report = await evaluate_demo(
        [{
            "case_id": "grounded",
            "query": "介绍灵山大佛",
            "expected_routes": ["hybrid"],
            "should_refuse": False,
            "required_terms": ["灵山大佛"],
            "citation_required": True,
        }],
        StubCoordinator(result),
        answer,
    )
    assert report["grounded_answer_accuracy"] == 1.0
    assert report["citation_canonical_rate"] == 1.0
    assert report["citation_locator_rate"] == 1.0
