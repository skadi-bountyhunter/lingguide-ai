"""景区天气 API 的无锡锁定与响应契约测试。"""
import pytest

from app.api import weather as weather_api


@pytest.mark.asyncio
async def test_weather_api_ignores_location_overrides_and_uses_wuxi(client, monkeypatch):
    calls = []

    async def fake_weather(city, scope):
        calls.append((city, scope))
        return {
            "ok": True,
            "status": "ready",
            "place": "无锡灵山胜境",
            "live": {"weather": "晴", "temperature": "25"},
            "casts": [],
        }

    monkeypatch.setattr(weather_api.amap_tools, "amap_weather_raw", fake_weather)
    response = await client.get(
        "/api/weather",
        params={"locale": "zh-CN", "city": "福建灵山", "scope": "福州"},
    )

    assert response.status_code == 200
    assert response.json()["place"] == "无锡灵山胜境"
    assert calls == [("灵山胜境", "无锡")]


@pytest.mark.asyncio
async def test_weather_openapi_only_exposes_locale(client):
    response = await client.get("/openapi.json")
    parameters = response.json()["paths"]["/api/weather"]["get"]["parameters"]

    assert [item["name"] for item in parameters] == ["locale"]


@pytest.mark.asyncio
async def test_weather_error_response_does_not_leak_key_or_request_params(client, monkeypatch):
    async def fake_weather(_city, _scope):
        return {
            "ok": False,
            "status": "error",
            "place": "无锡灵山胜境",
            "live": None,
            "casts": [],
            "message": "天气服务暂不可用，请稍后重试",
            "reason": "provider_error",
            "provider_code": "10001",
            "stage": "forecast",
        }

    monkeypatch.setattr(weather_api.amap_tools, "amap_weather_raw", fake_weather)
    response = await client.get("/api/weather", params={"city": "福建灵山", "scope": "福州"})
    body = response.text

    assert response.status_code == 200
    assert response.json()["reason"] == "provider_error"
    assert response.json()["provider_code"] == "10001"
    assert "福建灵山" not in body
    assert "福州" not in body
    assert "key" not in body.lower()
