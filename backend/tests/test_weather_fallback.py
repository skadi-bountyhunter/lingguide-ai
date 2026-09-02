"""天气地点路由、deadline、缓存和降级语义测试。"""
from types import SimpleNamespace

import pytest

from app.core import tools
from app.core.tools import amap_tools
from app.services import query_coordinator as coordinator_module
from app.services.answer_orchestrator import build_evidence_context


@pytest.fixture(autouse=True)
def clear_weather_cache():
    amap_tools.clear_weather_cache()
    yield
    amap_tools.clear_weather_cache()


def weather_payload(city="杭州", temperature="25"):
    return {
        "geocodes": [{
            "province": "浙江省",
            "city": city,
            "district": "西湖区",
            "formatted_address": f"浙江省{city}市西湖区",
            "adcode": "330100",
        }]
    }


@pytest.mark.parametrize("query", [
    "本景区天气怎么样", "景区今天天气怎么样", "这里天气怎么样", "这边气温多少",
    "当地明天会下雨吗", "现场风力怎么样", "附近要不要带伞", "本园区天气怎么样",
])
def test_weather_location_maps_scenic_context_to_wuxi(query):
    assert coordinator_module.QueryCoordinator._weather_location(query) == ("灵山胜境", "无锡")


@pytest.mark.parametrize(("query", "expected"), [
    ("杭州今天天气怎么样", "杭州"),
    ("今天杭州天气怎么样", "杭州"),
    ("无锡明天会不会下雨", "无锡"),
    ("杭州西湖区现在温度", "杭州西湖区"),
])
def test_weather_location_keeps_explicit_city(query, expected):
    assert coordinator_module.QueryCoordinator._weather_location(query) == (expected, None)


@pytest.mark.parametrize("query", [
    "灵山天气怎么样", "灵山景区今天会下雨吗", "灵山胜境气温多少", "灵山大佛风力怎么样", "无锡灵山天气",
])
def test_weather_location_maps_scenic_aliases_to_wuxi(query):
    assert coordinator_module.QueryCoordinator._weather_location(query) == ("灵山胜境", "无锡")


def test_foreign_lingshan_does_not_pollute_following_scenic_context():
    assert coordinator_module.QueryCoordinator._weather_location("福建灵山天气怎么样") == ("福建灵山", None)
    assert coordinator_module.QueryCoordinator._weather_location("这里天气怎么样") == ("灵山胜境", "无锡")


@pytest.mark.asyncio
async def test_explicit_weather_location_overrides_default(monkeypatch):
    monkeypatch.setattr(amap_tools.settings, "amap_web_key", "configured")
    calls = []

    async def fake_get(url, params, timeout=8.0, *, stage=None):
        calls.append((url, params, timeout))
        if "geocode" in url:
            return weather_payload("杭州")
        if params["extensions"] == "all":
            return {"forecasts": [{"casts": [{"date": "2026-07-18", "dayweather": "晴"}]}]}
        return {"lives": [{"weather": "晴", "temperature": "25", "reporttime": "10:00"}]}

    monkeypatch.setattr(amap_tools, "_amap_get", fake_get)
    result = await coordinator_module.query_coordinator.retrieve_async("杭州天气怎么样？")

    assert result.route == "weather"
    assert result.trace.channels["weather"]["place"] == "浙江省杭州市西湖区"
    assert calls[0][1]["address"] == "杭州"
    assert calls[0][1].get("city") is None


@pytest.mark.asyncio
async def test_weather_without_location_uses_configured_default(monkeypatch):
    monkeypatch.setattr(amap_tools.settings, "amap_web_key", "configured")
    monkeypatch.setattr(amap_tools.settings, "weather_default_city", "灵山胜境")
    monkeypatch.setattr(amap_tools.settings, "weather_default_scope", "无锡")
    calls = []

    async def fake_get(url, params, timeout=8.0, *, stage=None):
        calls.append((params, stage))
        if stage == "forecast":
            return {"forecasts": [{"casts": [{"date": "2026-07-18"}]}]}
        return {"lives": [{"temperature": "24"}]}

    monkeypatch.setattr(amap_tools, "_amap_get", fake_get)
    result = await coordinator_module.query_coordinator.retrieve_async("今天适合带伞吗？")

    assert result.route == "weather"
    assert len(calls) == 2
    assert {stage for _, stage in calls} == {"forecast", "live"}
    assert all(params["city"] == "320211" for params, _ in calls)
    assert all("address" not in params for params, _ in calls)


@pytest.mark.asyncio
async def test_weather_timeout_returns_degraded_without_evidence(monkeypatch):
    monkeypatch.setattr(amap_tools.settings, "amap_web_key", "configured")

    async def slow_get(*_args, **_kwargs):
        raise amap_tools.AmapRequestError("timeout")

    monkeypatch.setattr(amap_tools, "_amap_get", slow_get)
    result = await coordinator_module.query_coordinator.retrieve_async("杭州天气")

    assert result.degraded is True
    assert result.results == []
    assert result.citations == []
    assert result.fallback_reason == "timeout"
    assert result.trace.channels["weather"]["reason"] == "timeout"
    assert build_evidence_context(result) == ""


@pytest.mark.asyncio
async def test_weather_provider_error_is_not_ready(monkeypatch):
    monkeypatch.setattr(amap_tools.settings, "amap_web_key", "configured")

    async def provider_error(*_args, **_kwargs):
        raise amap_tools.AmapRequestError("http_503")

    monkeypatch.setattr(amap_tools, "_amap_get", provider_error)
    result = await coordinator_module.query_coordinator.retrieve_async("杭州天气")

    assert result.degraded is True
    assert result.trace.fallback_reason == "http_503"
    assert result.trace.channels["weather"]["status"] == "error"
    assert not result.citations


@pytest.mark.asyncio
async def test_fresh_cache_skips_provider(monkeypatch):
    monkeypatch.setattr(amap_tools.settings, "amap_web_key", "configured")
    call_count = 0

    async def fake_get(url, params, timeout=8.0, *, stage=None):
        nonlocal call_count
        call_count += 1
        if "geocode" in url:
            return weather_payload("杭州")
        return {"forecasts": [{"casts": [{"date": "2026-07-18"}]}], "lives": [{"temperature": "25"}]}

    monkeypatch.setattr(amap_tools, "_amap_get", fake_get)
    first = await amap_tools.amap_weather_raw("杭州")
    second = await amap_tools.amap_weather_raw("杭州")

    assert first["status"] == "ready"
    assert second["reason"] == "fresh_cache"
    assert call_count == 3


@pytest.mark.asyncio
async def test_stale_cache_is_exposed_but_never_becomes_evidence(monkeypatch):
    monkeypatch.setattr(amap_tools.settings, "amap_web_key", "configured")
    monkeypatch.setattr(amap_tools.settings, "weather_cache_ttl_seconds", 1.0)
    monkeypatch.setattr(amap_tools.settings, "weather_stale_window_seconds", 60.0)
    current_time = [100.0]
    monkeypatch.setattr(amap_tools.time, "monotonic", lambda: current_time[0])

    async def fake_get(url, params, timeout=8.0, *, stage=None):
        if "geocode" in url:
            return weather_payload("杭州")
        return {"forecasts": [{"casts": [{"date": "2026-07-18"}]}], "lives": [{"temperature": "25"}]}

    monkeypatch.setattr(amap_tools, "_amap_get", fake_get)
    await amap_tools.amap_weather_raw("杭州")
    current_time[0] = 102.0

    async def failed_get(*_args, **_kwargs):
        raise amap_tools.AmapRequestError("http_429")

    monkeypatch.setattr(amap_tools, "_amap_get", failed_get)
    stale = await amap_tools.amap_weather_raw("杭州")
    evidence = await amap_tools.amap_weather_evidence("杭州")
    result = coordinator_module.weather_to_query_result(evidence)

    assert stale["status"] == "stale"
    assert stale["reason"] == "http_429"
    assert evidence["status"] == "stale"
    assert result.degraded is True
    assert result.results == []
    assert result.citations == []
    assert build_evidence_context(result) == ""
