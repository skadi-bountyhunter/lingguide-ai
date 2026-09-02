"""数据大屏真实统计回归测试。"""
from datetime import datetime, timezone

import pytest

from app.models import Interaction
from app.services.dashboard_service import get_overview
from app.services import chat_service


async def _add_interaction(
    *,
    interaction_id: str,
    session_id: str,
    query_text: str,
    created_at: datetime,
    query_mode: str = "text",
    emotion_score: float = 0.5,
    thinking_time_ms: int = 100,
) -> None:
    async for db in chat_service.db_provider():
        db.add(Interaction(
            id=interaction_id,
            session_id=session_id,
            query_text=query_text,
            response_text="测试回答",
            query_mode=query_mode,
            emotion_score=emotion_score,
            thinking_time_ms=thinking_time_ms,
            created_at=created_at,
        ))
        await db.commit()


async def _overview(period: str, now: datetime) -> dict:
    async for db in chat_service.db_provider():
        return await get_overview(db, period, now)
    raise AssertionError("测试数据库会话不可用")


@pytest.mark.asyncio
async def test_today_uses_china_business_day_and_real_aggregates(client):
    now = datetime(2026, 7, 19, 4, 10, tzinfo=timezone.utc)  # 北京时间 12:10
    await _add_interaction(
        interaction_id="before-china-day",
        session_id="outside",
        query_text="不应统计",
        created_at=datetime(2026, 7, 18, 15, 59, 59),
    )
    await _add_interaction(
        interaction_id="at-china-day-start",
        session_id="session-a",
        query_text="重复问题",
        created_at=datetime(2026, 7, 18, 16, 0),
        query_mode="text",
        emotion_score=0.8,
        thinking_time_ms=100,
    )
    await _add_interaction(
        interaction_id="second-session-a",
        session_id="session-a",
        query_text="重复问题",
        created_at=datetime(2026, 7, 19, 4, 0),
        query_mode="voice",
        emotion_score=0.4,
        thinking_time_ms=0,
    )
    await _add_interaction(
        interaction_id="session-b",
        session_id="session-b",
        query_text="另一个问题",
        created_at=datetime(2026, 7, 19, 4, 8),
        query_mode="custom-mode",
        emotion_score=1.2,
        thinking_time_ms=300,
    )

    body = await _overview("today", now)

    assert body["timezone"] == "Asia/Shanghai"
    assert body["range"]["start"] == "2026-07-19T00:00:00+08:00"
    assert body["summary"]["interaction_count"] == 3
    assert body["summary"]["session_count"] == 2
    assert body["summary"]["avg_thinking_time_ms"] == {"value": 200.0, "sample_count": 2}
    assert body["summary"]["avg_emotion_score"] == {"value": 0.6, "sample_count": 2}
    assert body["activity"]["active_session_count"] == 2
    assert body["activity"]["interaction_count"] == 2
    assert body["mode_distribution"]["items"] == [
        {"mode": "text", "count": 1, "ratio": 0.3333},
        {"mode": "voice", "count": 1, "ratio": 0.3333},
        {"mode": "other", "count": 1, "ratio": 0.3333},
    ]
    assert sum(bucket["count"] for bucket in body["interaction_trend"]["buckets"]) == 3
    assert body["top_questions"] == [
        {"question": "重复问题", "count": 2},
        {"question": "另一个问题", "count": 1},
    ]


@pytest.mark.asyncio
async def test_empty_dashboard_keeps_missing_averages_as_null(client):
    body = await _overview("today", datetime(2026, 7, 19, 4, 10, tzinfo=timezone.utc))

    assert body["summary"]["interaction_count"] == 0
    assert body["summary"]["session_count"] == 0
    assert body["summary"]["avg_thinking_time_ms"] == {"value": None, "sample_count": 0}
    assert body["summary"]["avg_emotion_score"] == {"value": None, "sample_count": 0}
    assert body["top_questions"] == []
    assert all(bucket["count"] == 0 for bucket in body["interaction_trend"]["buckets"])
    assert all(bucket["avg_score"] is None for bucket in body["emotion_trend"]["buckets"])
    assert all(item["ratio"] is None for item in body["mode_distribution"]["items"])


@pytest.mark.asyncio
async def test_dashboard_api_accepts_periods_and_rejects_invalid_values(client):
    for period in ("today", "7d", "30d"):
        response = await client.get(f"/api/dashboard/overview?period={period}")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["period"] == period

    response = await client.get("/api/dashboard/overview?period=invalid")
    assert response.status_code == 422
