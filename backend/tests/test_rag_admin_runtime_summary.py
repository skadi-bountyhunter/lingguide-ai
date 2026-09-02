"""RAG 最近运行摘要接口回归测试。"""
import pytest

from app.models import Interaction
from app.services import chat_service


async def _log(
    session_id: str,
    *,
    thinking_time_ms: int,
    retrieval: dict,
) -> None:
    await chat_service.log_interaction(
        session_id=session_id,
        query_text="不应出现在摘要中",
        response_text="不应出现在摘要中",
        thinking_time_ms=thinking_time_ms,
        retrieval=retrieval,
        trace_id=f"trace-{session_id}",
    )


@pytest.mark.asyncio
async def test_runtime_summary_aggregates_recent_low_sensitivity_metrics(client):
    await _log(
        "summary-normal",
        thinking_time_ms=100,
        retrieval={
            "latency_ms": 40,
            "degraded": False,
            "channels": {
                "structured": {"status": "ok", "latency_ms": 10},
                "fts": {"status": "empty", "latency_ms": 20},
                "bge": {"status": "skipped", "latency_ms": 0},
                "weather": {"status": "skipped", "latency_ms": 0},
                "llm": {"status": "ok", "latency_ms": 60},
            },
        },
    )
    await _log(
        "summary-degraded",
        thinking_time_ms=300,
        retrieval={
            "latency_ms": 140,
            "degraded": True,
            "channels": {
                "structured": {"status": "timeout", "latency_ms": 80},
                "fts": {"status": "failed", "latency_ms": 40},
                "bge": {"status": "ok", "latency_ms": 20},
                "weather": {"status": "skipped", "latency_ms": 0},
                "llm": {"status": "skipped", "latency_ms": 0},
            },
        },
    )

    response = await client.get("/api/rag-admin/runtime-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["window_size"] == 100
    assert body["request_count"] == 2
    assert body["end_to_end"] == {"sample_count": 2, "p50_ms": 200.0, "p95_ms": 290.0}
    assert body["retrieval"] == {"sample_count": 2, "p50_ms": 90.0, "p95_ms": 135.0}
    assert body["degraded"] == {"count": 1, "rate": 0.5}
    assert body["channel_abnormal"] == {"count": 1, "rate": 0.5}
    assert body["channels"]["structured"] == {"sample_count": 2, "avg_latency_ms": 45.0}
    assert body["channels"]["fts"] == {"sample_count": 2, "avg_latency_ms": 30.0}
    assert body["channels"]["bge"] == {"sample_count": 1, "avg_latency_ms": 20.0}
    assert body["channels"]["weather"] == {"sample_count": 0, "avg_latency_ms": None}
    assert body["channels"]["llm"] == {"sample_count": 1, "avg_latency_ms": 60.0}
    assert "query_text" not in body
    assert "response_text" not in body
    assert "trace_id" not in body


@pytest.mark.asyncio
async def test_runtime_summary_ignores_invalid_history_records(client):
    async for db in chat_service.db_provider():
        db.add(Interaction(
            id="invalid-runtime-summary",
            session_id="invalid",
            query_text="敏感原文",
            response_text="敏感回答",
            retrieval_json="not-json",
            trace_id="trace-invalid",
        ))
        await db.commit()

    response = await client.get("/api/rag-admin/runtime-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["request_count"] == 0
    assert body["first_recorded_at"] is None
    assert body["last_recorded_at"] is None
    assert body["end_to_end"] == {"sample_count": 0, "p50_ms": 0.0, "p95_ms": 0.0}
    assert body["retrieval"] == {"sample_count": 0, "p50_ms": 0.0, "p95_ms": 0.0}
    assert body["channels"]["llm"] == {"sample_count": 0, "avg_latency_ms": None}
