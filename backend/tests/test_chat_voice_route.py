"""语音路线请求的结构化快照回归测试。"""
import pytest

from app.api import chat as chat_api
from app.api.chat import RouteResponse, RouteSpot


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "duration_mode"),
    [
        ("请规划一条半天游路线", "半天"),
        ("请安排一条全天路线", "全天"),
    ],
)
async def test_voice_route_returns_chat_snapshot(client, monkeypatch, query, duration_mode):
    async def transcribe(*_args, **_kwargs):
        return query

    async def generate_route(request, **_kwargs):
        assert request.chat_query == query
        assert request.duration == duration_mode
        return RouteResponse(
            title="语音路线",
            duration=f"约{duration_mode}",
            spots=[
                RouteSpot(name="梵宫", description="欣赏建筑艺术"),
                RouteSpot(name="九龙灌浴", description="观看精彩表演"),
            ],
            tips="请提前确认表演时间",
            route_text="先游览梵宫，再观看九龙灌浴。",
            sources=["测试知识库"],
            citations=[{"source": "测试知识库"}],
            retrieval={"status": "ready"},
            trace_id="voice-route-trace",
        )

    async def synthesize(*_args, **_kwargs):
        return b"audio"

    async def log(*_args, **_kwargs):
        return None

    monkeypatch.setattr(chat_api, "transcribe_audio", transcribe)
    monkeypatch.setattr(chat_api, "generate_route", generate_route)
    monkeypatch.setattr(chat_api, "synthesize", synthesize)
    monkeypatch.setattr(chat_api, "log_interaction", log)

    response = await client.post(
        "/api/chat/voice",
        data={"session_id": "voice-route", "interests": '["建筑艺术"]'},
        files={"audio": ("question.wav", b"audio", "audio/wav")},
    )

    assert response.status_code == 200
    body = response.json()
    snapshot = body["route_plan"]
    assert snapshot["schema_version"] == 1
    assert snapshot["source"] == "chat"
    assert snapshot["duration_mode"] == duration_mode
    assert [spot["name"] for spot in snapshot["spots"]] == ["梵宫", "九龙灌浴"]
    assert body["reply"] == "先游览梵宫，再观看九龙灌浴。"


@pytest.mark.asyncio
async def test_voice_non_route_does_not_return_snapshot(client, monkeypatch):
    async def transcribe(*_args, **_kwargs):
        return "介绍一下灵山大佛"

    async def retrieve(*_args, **_kwargs):
        class Result:
            route = "faq"
            results = [type("Answer", (), {"content": "灵山大佛高88米"})()]
            sources = ["测试知识库"]
            citations = []
            trace = type("Trace", (), {"to_dict": lambda self: {"status": "ready"}})()
            trace_id = "voice-faq-trace"

        return Result()

    async def synthesize(*_args, **_kwargs):
        return b"audio"

    async def log(*_args, **_kwargs):
        return None

    monkeypatch.setattr(chat_api, "transcribe_audio", transcribe)
    monkeypatch.setattr(chat_api.query_coordinator, "retrieve_async", retrieve)
    monkeypatch.setattr(chat_api, "synthesize", synthesize)
    monkeypatch.setattr(chat_api, "log_interaction", log)

    response = await client.post(
        "/api/chat/voice",
        data={"session_id": "voice-faq", "interests": "[]"},
        files={"audio": ("question.wav", b"audio", "audio/wav")},
    )

    assert response.status_code == 200
    assert "route_plan" not in response.json()
