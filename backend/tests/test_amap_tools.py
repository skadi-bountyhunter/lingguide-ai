"""高德天气地点归一化与错误闭环测试。"""
from types import SimpleNamespace

import pytest

from app.core.tools import amap_tools


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["灵山", "灵山大佛", "本景区", "这里", "附近"])
async def test_scenic_location_uses_fixed_wuxi_adcode_without_geocode(monkeypatch, value):
    async def unexpected_get(*_args, **_kwargs):
        raise AssertionError("默认景区不应调用地理编码")

    monkeypatch.setattr(amap_tools, "_amap_get", unexpected_get)
    adcode, place = await amap_tools._resolve_adcode(value, "福州")

    assert adcode == "320211"
    assert "无锡" in place
    assert "灵山胜境" in place


@pytest.mark.parametrize("value", ["景区", "本景区", "景区今天", "本景区今天会", "这里", "这边", "附近", "本园区"])
def test_scenic_context_normalizes_to_configured_wuxi(value):
    assert amap_tools._normalize_location(value) == ("灵山胜境", "无锡", True)


def test_scenic_aliases_share_normalized_location():
    assert amap_tools._normalize_location("灵山") == amap_tools._normalize_location("灵山大佛")
    assert amap_tools._normalize_location("灵山大佛", "福州") == ("灵山胜境", "无锡", True)
    assert amap_tools._normalize_location("灵山大佛附近") == ("灵山胜境", "无锡", True)


def test_foreign_lingshan_is_not_rewritten_to_wuxi():
    assert amap_tools._normalize_location("福建灵山") == ("福建灵山", None, False)
    assert amap_tools._weather_key("福建灵山", None, "all") != amap_tools._weather_key("灵山", None, "all")


@pytest.mark.asyncio
async def test_raw_weather_empty_data_is_failure(monkeypatch):
    monkeypatch.setattr(amap_tools.settings, "amap_web_key", "test-key")
    calls = []

    async def fake_get(url, params, timeout=8.0, *, stage=None):
        calls.append((url, params, stage))
        return {"forecasts": [], "lives": []}

    monkeypatch.setattr(amap_tools, "_amap_get", fake_get)
    result = await amap_tools.amap_weather_raw("灵山")

    assert result["ok"] is False
    assert "暂无可用数据" in result["message"]
    assert len(calls) == 2
    assert {stage for _, _, stage in calls} == {"forecast", "live"}
    assert all(params["city"] == "320211" for _, params, _ in calls)
    assert all("address" not in params for _, params, _ in calls)


@pytest.mark.asyncio
async def test_provider_error_keeps_safe_code_and_stage(monkeypatch):
    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"status": "0", "info": "INVALID_USER_KEY", "infocode": "10001"}

    async def fake_get(*_args, **_kwargs):
        return FakeResponse()

    monkeypatch.setattr(amap_tools, "_get_http_client", lambda: SimpleNamespace(get=fake_get))

    with pytest.raises(amap_tools.AmapRequestError) as error:
        await amap_tools._amap_get(
            "https://restapi.amap.com/v3/weather/weatherInfo",
            {"key": "test-secret-key"},
            stage="forecast",
        )

    assert error.value.reason == "provider_error"
    assert error.value.provider_code == "10001"
    assert error.value.stage == "forecast"
    assert "test-secret-key" not in str(error.value)
