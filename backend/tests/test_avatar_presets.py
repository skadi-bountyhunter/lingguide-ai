"""星云数字人角色预设 API 回归测试。"""

import pytest

from app.config import settings


@pytest.mark.asyncio
async def test_avatar_presets_persist_and_hide_sdk_secrets(client, monkeypatch):
    monkeypatch.setattr(settings, "xingyun_default_guide_app_id", "")
    monkeypatch.setattr(settings, "xingyun_default_guide_app_secret", "")
    monkeypatch.setattr(settings, "xingyun_preset_credentials", "")

    initial = await client.get("/api/avatar/presets")
    assert initial.status_code == 200
    default = next(item for item in initial.json()["presets"] if item["preset_key"] == "default_guide")
    assert default["is_active"] is True
    assert default["sdk_configured"] is False
    assert "app_secret" not in default

    created = await client.post("/api/avatar/presets", json={
        "preset_key": "culture_guide",
        "name": "文化讲解员",
        "description": "用于传统文化主题讲解。",
        "scene_label": "文化讲解",
        "voice_label": "温柔女声",
        "performance_style": "古风讲解",
        "sort_order": 10,
        "app_id": "xingyun-app-id",
        "app_secret": "xingyun-app-secret",
    })
    assert created.status_code == 201
    assert created.json()["sdk_configured"] is True
    assert created.json()["app_id"] == "xingyun-app-id"
    assert created.json()["secret_masked"] == "****************"
    assert "xingyun-app-secret" not in created.text

    credentials = await client.get("/api/avatar/presets/culture_guide/credentials")
    assert credentials.status_code == 200
    assert credentials.json()["app_id"] == "xingyun-app-id"
    assert credentials.json()["sdk_configured"] is True
    assert credentials.json()["secret_masked"] == "****************"
    assert "app_secret" not in credentials.json()

    activated = await client.post("/api/avatar/presets/culture_guide/activate")
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True
    assert activated.json()["sdk_configured"] is True
    assert "xingyun-app-secret" not in activated.text

    active = await client.get("/api/avatar/active")
    assert active.status_code == 200
    body = active.json()
    assert body["preset_key"] == "culture_guide"
    assert body["available"] is True
    assert body["gateway_url"] == "/api/avatar/session/culture_guide"
    assert active.headers["cache-control"] == "no-store"
    assert "app_secret" not in body
    assert "xingyun-app-secret" not in active.text

    monkeypatch.setattr(settings, "xingyun_default_guide_app_id", "legacy-app-id")
    monkeypatch.setattr(settings, "xingyun_default_guide_app_secret", "legacy-app-secret")
    default_credentials = await client.get("/api/avatar/presets/default_guide/credentials")
    assert default_credentials.status_code == 200
    assert default_credentials.json()["app_id"] == "legacy-app-id"
    assert default_credentials.json()["sdk_configured"] is True
    assert "app_secret" not in default_credentials.json()

    preserved = await client.put("/api/avatar/presets/culture_guide", json={
        "name": "文化讲解员（更新）",
        "app_id": "",
        "app_secret": "",
    })
    assert preserved.status_code == 200
    assert preserved.json()["sdk_configured"] is True

    cleared = await client.put("/api/avatar/presets/culture_guide", json={
        "name": "文化讲解员（更新）",
        "clear_credentials": True,
    })
    assert cleared.status_code == 200
    assert cleared.json()["sdk_configured"] is False

    reloaded = await client.get("/api/avatar/presets")
    selected = next(item for item in reloaded.json()["presets"] if item["preset_key"] == "culture_guide")
    assert selected["is_active"] is True


@pytest.mark.asyncio
async def test_avatar_presets_reject_duplicate_keys_and_active_deletion(client):
    first = await client.post("/api/avatar/presets", json={
        "preset_key": "family_guide",
        "name": "亲子讲解员",
    })
    assert first.status_code == 201

    duplicate = await client.post("/api/avatar/presets", json={
        "preset_key": "family_guide",
        "name": "重复角色",
    })
    assert duplicate.status_code == 409

    default_delete = await client.delete("/api/avatar/presets/default_guide")
    assert default_delete.status_code == 422
