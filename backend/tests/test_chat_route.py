"""数字人路线规划专项回归测试。"""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api import chat
from app.core import llm
from app.core.llm import LLMGenerationError


SPOT_ITEMS = [
    {"name": "灵山大佛", "tags": ["佛教文化"], "desc": "世界著名青铜立佛"},
    {"name": "梵宫", "tags": ["建筑艺术"], "desc": "华美佛教艺术殿堂"},
    {"name": "九龙灌浴", "tags": ["亲子游乐"], "desc": "大型动态音乐喷泉"},
    {"name": "五印坛城", "tags": ["建筑艺术"], "desc": "藏传佛教文化建筑"},
    {"name": "祥符禅寺", "tags": ["历史古迹"], "desc": "千年佛教禅寺"},
    {"name": "菩提大道", "tags": ["自然风光"], "desc": "景区林荫步道"},
    {"name": "灵山大照壁", "tags": ["历史古迹"], "desc": "灵山胜境入口景观"},
    {"name": "佛足坛", "tags": ["佛教文化"], "desc": "佛教文化景观"},
    {"name": "百子戏弥勒", "tags": ["亲子游乐"], "desc": "生动有趣的群雕"},
]


class FakeSpot:
    def __init__(self, item: dict):
        self.name = item["name"]
        self.tags_list = item["tags"]
        self.desc = item["desc"]


class FakeScalars:
    def all(self):
        return [FakeSpot(item) for item in SPOT_ITEMS]


class FakeResult:
    def scalars(self):
        return FakeScalars()


class FakeSession:
    async def execute(self, _statement):
        return FakeResult()


class FakeSessionContext:
    async def __aenter__(self):
        return FakeSession()

    async def __aexit__(self, exc_type, exc, tb):
        return False


def fake_async_session():
    return FakeSessionContext()


@pytest.fixture(autouse=True)
def isolate_route_dependencies(monkeypatch):
    monkeypatch.setattr(chat, "async_session", fake_async_session)
    monkeypatch.setattr(chat.rag_service, "search", lambda *_args, **_kwargs: [])


def response_generator(payload=None, error=None):
    async def generate(*_args, **_kwargs):
        if error:
            raise error
        yield payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)

    return generate


@pytest.mark.asyncio
async def test_generate_response_can_disable_chat_mock(monkeypatch):
    monkeypatch.setattr(llm, "_get_client", lambda: None)

    with pytest.raises(LLMGenerationError):
        async for _ in llm.generate_response(
            "路线",
            "灵山胜境",
            allow_mock_fallback=False,
        ):
            pass

    chunks = []
    async for chunk in llm.generate_response("路线", "灵山胜境"):
        chunks.append(chunk)
    assert "灵山大佛" in "".join(chunks)


@pytest.mark.asyncio
async def test_single_json_spot_is_completed_to_half_day_route(monkeypatch):
    monkeypatch.setattr(chat, "generate_response", response_generator({
        "title": "大佛经典游",
        "duration": "约4小时",
        "spots": [{"name": "灵山大佛", "description": "朝拜祈福"}],
        "tips": "错峰游览",
    }))

    result = await chat.generate_route(chat.RouteRequest(
        duration="半天",
        chat_query="先去梵宫，再看九龙灌浴，最后去灵山大佛",
        chat_reply="我还推荐五印坛城和祥符禅寺",
    ))

    assert [spot.name for spot in result.spots] == [
        "梵宫", "九龙灌浴", "灵山大佛", "五印坛城", "祥符禅寺",
    ]
    assert len({spot.name for spot in result.spots}) == 5


@pytest.mark.asyncio
async def test_numbered_route_keeps_multiple_lines(monkeypatch):
    monkeypatch.setattr(chat, "generate_response", response_generator(
        "1. 灵山大佛 — 朝拜祈福\n"
        "2. 梵宫 — 欣赏艺术\n"
        "3. 九龙灌浴 — 观看表演"
    ))

    result = await chat.generate_route(chat.RouteRequest(duration="半天"))

    assert [spot.name for spot in result.spots[:3]] == ["灵山大佛", "梵宫", "九龙灌浴"]
    assert len(result.spots) == 5


@pytest.mark.asyncio
async def test_llm_failure_uses_real_spots_and_reply_context(monkeypatch):
    monkeypatch.setattr(
        chat,
        "generate_response",
        response_generator(error=LLMGenerationError("timeout")),
    )

    result = await chat.generate_route(chat.RouteRequest(
        interests=["历史古迹"],
        duration="半天",
        chat_query="就按刚才说的安排",
        chat_reply="建议先游览梵宫，再去九龙灌浴和五印坛城。",
    ))

    names = [spot.name for spot in result.spots]
    assert names[:3] == ["梵宫", "九龙灌浴", "五印坛城"]
    assert len(names) == 5
    assert len(set(names)) == 5
    assert set(names) <= {item["name"] for item in SPOT_ITEMS}


@pytest.mark.asyncio
@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
async def test_non_chinese_llm_failure_localizes_deterministic_fallback(monkeypatch, locale):
    monkeypatch.setattr(
        chat,
        "generate_response",
        response_generator(error=LLMGenerationError("timeout")),
    )

    result = await chat.generate_route(chat.RouteRequest(
        interests=["佛教文化"],
        duration="半天",
        locale=locale,
    ))

    assert result.title == chat.message("route_fallback_title", locale)
    assert result.duration == chat.localize_duration("约半天", locale)
    assert result.tips == chat.message("route_fallback_tips", locale)
    assert all(spot.name in {item["name"] for item in SPOT_ITEMS} for spot in result.spots)
    assert all(spot.display_name and spot.display_name != spot.name for spot in result.spots)
    assert all(spot.description and not spot.description.startswith("世界著名") for spot in result.spots)
    assert "景区特色景点" not in result.route_text


@pytest.mark.asyncio
@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
async def test_non_chinese_route_rejects_wrong_language_fields(monkeypatch, locale):
    monkeypatch.setattr(chat, "generate_response", response_generator({
        "title": "中文路线标题",
        "duration": "约4小时",
        "spots": [{"name": "灵山大佛", "description": "中文景点说明"}],
        "tips": "中文游览提示",
    }))

    result = await chat.generate_route(chat.RouteRequest(duration="半天", locale=locale))

    assert result.title == chat.message("route_fallback_title", locale)
    assert result.duration == chat.localize_duration("约半天", locale)
    assert result.tips == chat.message("route_fallback_tips", locale)
    assert result.spots[0].description != "中文景点说明"
    assert chat.matches_target_language(result.spots[0].description, locale)


@pytest.mark.asyncio
async def test_all_day_route_is_capped_at_eight(monkeypatch):
    monkeypatch.setattr(chat, "generate_response", response_generator({
        "title": "全天精华游",
        "duration": "约8小时",
        "spots": [
            {"name": item["name"], "description": item["desc"]}
            for item in SPOT_ITEMS
        ],
        "tips": "",
    }))

    result = await chat.generate_route(chat.RouteRequest(duration="全天"))

    assert len(result.spots) == 8
    assert [spot.name for spot in result.spots] == [item["name"] for item in SPOT_ITEMS[:8]]
