"""多语言契约专项测试：仅使用 mock，不访问外网。"""
from types import SimpleNamespace

import pytest

from app.api import chat
from app.api.routes import SEED_ROUTES
from app.core import asr, llm, tts
from app.core.locales import normalize_locale, project_spot
from app.api.spots import _to_out as spot_to_out
from app.services import answer_orchestrator
from app.services.query_coordinator import QueryResult


def test_locale_normalization_and_spot_projection():
    assert normalize_locale("en-US") == "en"
    assert normalize_locale("ja_JP") == "ja"
    assert normalize_locale("unknown") == "zh-CN"
    spot = SimpleNamespace(name="灵山大佛", desc="中文简介", full_desc="中文详情", tags_list=["佛教文化"], highlights_list=[], tips_list=[], nearby_list=[])
    projected = project_spot(spot, "en")
    assert projected["canonical_name"] == "灵山大佛"
    assert projected["display_name"] == "Lingshan Grand Buddha"
    assert projected["display_tags"] == ["Buddhist culture", "Architecture"]
    assert projected["translation_status"] == "translated"


def test_spot_response_keeps_canonical_tags_and_nearby():
    spot = SimpleNamespace(
        id=1, name="灵山大佛", icon="", image="", desc="中文简介", full_desc="中文详情",
        tags_list=["佛教文化", "建筑艺术"], duration="1h", distance="1km",
        highlights_list=[], hours="", ticket="", tips_list=[], best_season="",
        nearby_list=["梵宫"], lng=None, lat=None, sort_order=1,
    )
    result = spot_to_out(spot, "en")
    assert result.tags == ["Buddhist culture", "Architecture"]
    assert result.canonical_tags == ["佛教文化", "建筑艺术"]
    assert result.nearby == ["Brahma Palace"]
    assert result.canonical_nearby == ["梵宫"]


@pytest.mark.asyncio
@pytest.mark.parametrize("locale", ["en", "ja", "ko"])
async def test_preset_routes_expose_localized_display_and_canonical_spots(client, locale):
    created = await client.post("/api/routes", json=SEED_ROUTES[0])
    assert created.status_code == 201
    response = await client.get("/api/routes", params={"locale": locale})
    assert response.status_code == 200
    routes = response.json()
    assert len(routes) == 1
    assert all(route["display_title"] != route["title"] for route in routes)
    assert all(route["display_desc"] != route["desc"] for route in routes)
    assert all(route["display_tip"] != route["tip"] for route in routes)
    assert routes[0]["spots"][0] == "灵山大佛"
    assert routes[0]["display_spots"][0] != "灵山大佛"
    assert "佛教文化" in routes[0]["tags"]
    assert routes[0]["display_tags"]


@pytest.mark.asyncio
async def test_non_chinese_faq_uses_locale_aware_llm(monkeypatch):
    result = QueryResult([], route="faq")
    calls = []

    async def fake_generate(*args, **kwargs):
        calls.append(kwargs.get("locale"))
        yield "English answer"

    monkeypatch.setattr(answer_orchestrator, "generate_response", fake_generate)
    result.citations = [SimpleNamespace(id="C1")]
    result.results = [SimpleNamespace(content="中文 FAQ")]
    result.trace.channels = {}
    assert await answer_orchestrator.generate_answer("height", result, locale="en") == "English answer【C1】"
    assert calls == ["en"]


def test_prompt_has_target_language_and_preserves_citation_rule():
    prompt = llm._build_prompt("evidence", locale="ja")
    assert "日本語" in prompt
    assert "quote" in prompt


def test_tts_voice_whitelist_by_locale():
    assert tts.voice_for_locale("en") == "en-US-JennyNeural"
    assert tts.voice_for_locale("ja") == "ja-JP-NanamiNeural"
    assert tts.voice_for_locale("ko") == "ko-KR-SunHiNeural"
    assert tts.voice_for_locale("en", "zh-CN-XiaoxiaoNeural") == "en-US-JennyNeural"


@pytest.mark.asyncio
async def test_asr_non_chinese_is_stable_without_external_provider(monkeypatch):
    monkeypatch.setattr(asr.settings, "asr_provider", "unknown")
    result = await asr.transcribe_audio(b"audio", locale="en")
    assert "speech" in result.lower()
