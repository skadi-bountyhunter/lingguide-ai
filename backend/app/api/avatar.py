"""魔珐星云数字人预设管理 API。"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_admin
from app.config import settings
from app.core.database import get_db
from app.models import AvatarPreset

router = APIRouter(prefix="/api/avatar", tags=["数字人角色管理"])

_DEFAULT_PRESET_KEY = "default_guide"
_DEFAULT_PRESET = {
    "preset_key": _DEFAULT_PRESET_KEY,
    "name": "灵境讲解员",
    "description": "默认景区讲解角色，适用于日常问答与路线推荐。",
    "scene_label": "日常景区讲解",
    "voice_label": "温柔亲切",
    "performance_style": "自然讲解",
    "thumbnail_url": "",
    "sort_order": 0,
    "is_active": 1,
}


class AvatarPresetPayload(BaseModel):
    preset_key: str = Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    scene_label: str = Field(default="景区讲解", max_length=100)
    voice_label: str = Field(default="", max_length=100)
    performance_style: str = Field(default="", max_length=100)
    thumbnail_url: str = Field(default="", max_length=255)
    sort_order: int = Field(default=0, ge=0, le=9999)
    app_id: str = Field(default="", max_length=128)
    app_secret: str = Field(default="", max_length=512)


class AvatarPresetUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    scene_label: str = Field(default="景区讲解", max_length=100)
    voice_label: str = Field(default="", max_length=100)
    performance_style: str = Field(default="", max_length=100)
    thumbnail_url: str = Field(default="", max_length=255)
    sort_order: int = Field(default=0, ge=0, le=9999)
    app_id: str | None = Field(default=None, max_length=128)
    app_secret: str | None = Field(default=None, max_length=512)
    clear_credentials: bool = False


def _validate_credentials(app_id: str, app_secret: str) -> tuple[str, str]:
    """星云应用 ID 与 Secret 必须成对配置。"""
    app_id = app_id.strip()
    app_secret = app_secret.strip()
    if bool(app_id) != bool(app_secret):
        raise HTTPException(status_code=422, detail="星云应用 ID 与 Secret 必须同时填写")
    return app_id, app_secret


def _environment_credentials() -> dict[str, dict[str, Any]]:
    """读取旧环境变量凭据映射，作为历史默认角色的兼容回退。"""
    raw = settings.xingyun_preset_credentials.strip()
    parsed: dict[str, Any] = {}
    if raw:
        try:
            candidate = json.loads(raw)
            parsed = candidate if isinstance(candidate, dict) else {}
        except json.JSONDecodeError:
            parsed = {}
    default = {
        "app_id": settings.xingyun_default_guide_app_id.strip(),
        "app_secret": settings.xingyun_default_guide_app_secret.strip(),
        "gateway_url": settings.xingyun_gateway_url.strip(),
    }
    configured_default = parsed.get(_DEFAULT_PRESET_KEY)
    has_complete_default = isinstance(configured_default, dict) and bool(
        str(configured_default.get("app_id", "")).strip()
        and str(configured_default.get("app_secret", "")).strip()
    )
    if default["app_id"] and default["app_secret"] and not has_complete_default:
        parsed[_DEFAULT_PRESET_KEY] = default
    return {
        str(key): {
            "app_id": str(value.get("app_id", "")).strip(),
            "app_secret": str(value.get("app_secret", "")).strip(),
            "gateway_url": str(value.get("gateway_url") or settings.xingyun_gateway_url).strip(),
            "tag": str(value.get("tag", "")).strip(),
            "config": value.get("config") if isinstance(value.get("config"), dict) else {},
        }
        for key, value in parsed.items()
        if isinstance(value, dict)
    }


def _credential_for_preset(preset: AvatarPreset) -> dict[str, Any]:
    """优先使用后台保存的凭据，未保存时兼容旧环境变量配置。"""
    app_id, app_secret = _validate_credentials(preset.app_id or "", preset.app_secret or "")
    fallback = _environment_credentials().get(preset.preset_key, {})
    if app_id and app_secret:
        return {
            **fallback,
            "app_id": app_id,
            "app_secret": app_secret,
            "gateway_url": fallback.get("gateway_url") or settings.xingyun_gateway_url.strip(),
        }
    return fallback


def _configured(preset: AvatarPreset) -> bool:
    credential = _credential_for_preset(preset)
    return bool(credential.get("app_id") and credential.get("app_secret") and credential.get("gateway_url"))


def _mask_secret(secret: str) -> str:
    """角色列表只显示 Secret 的遮盖状态。"""
    return "*" * max(8, min(len(secret), 16)) if secret else ""


def _serialize(
    preset: AvatarPreset,
    *,
    include_runtime: bool = False,
    include_credential_status: bool = True,
) -> dict[str, Any]:
    credential = _credential_for_preset(preset)
    configured = bool(
        credential.get("app_id") and credential.get("app_secret") and credential.get("gateway_url")
    )
    payload = {
        "id": preset.id,
        "preset_key": preset.preset_key,
        "name": preset.name,
        "description": preset.description,
        "scene_label": preset.scene_label,
        "voice_label": preset.voice_label,
        "performance_style": preset.performance_style,
        "thumbnail_url": preset.thumbnail_url,
        "sort_order": preset.sort_order,
        "is_active": bool(preset.is_active),
        "sdk_configured": configured,
    }
    if include_credential_status:
        payload.update({
            "app_id": credential.get("app_id", ""),
            "secret_masked": _mask_secret(credential.get("app_secret", "")),
            "uses_legacy_credentials": not bool(preset.app_id and preset.app_secret) and configured,
        })
    if include_runtime:
        # SDK 当前要求浏览器侧拿到 gateway；同源路径会由服务端按预设重签。
        payload["gateway_url"] = f"/api/avatar/session/{preset.preset_key}"
    return payload


async def _ensure_default_preset(db: AsyncSession) -> AvatarPreset:
    preset = await db.scalar(select(AvatarPreset).where(AvatarPreset.preset_key == _DEFAULT_PRESET_KEY))
    if preset:
        return preset
    preset = AvatarPreset(**_DEFAULT_PRESET)
    db.add(preset)
    await db.commit()
    await db.refresh(preset)
    return preset


async def _active_preset(db: AsyncSession) -> AvatarPreset:
    await _ensure_default_preset(db)
    preset = await db.scalar(
        select(AvatarPreset)
        .where(AvatarPreset.is_active == 1)
        .order_by(AvatarPreset.sort_order, AvatarPreset.created_at)
    )
    if preset:
        return preset
    preset = await db.scalar(select(AvatarPreset).where(AvatarPreset.preset_key == _DEFAULT_PRESET_KEY))
    if not preset:
        raise HTTPException(status_code=500, detail="默认数字人预设不存在")
    preset.is_active = 1
    await db.commit()
    await db.refresh(preset)
    return preset


@router.get("/presets")
async def list_presets(db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    """管理端获取全部角色预设，绝不返回 SDK 密钥。"""
    await _ensure_default_preset(db)
    rows = list((await db.execute(select(AvatarPreset).order_by(AvatarPreset.sort_order, AvatarPreset.created_at))).scalars())
    return {"presets": [_serialize(item) for item in rows]}


@router.get("/presets/{preset_key}/credentials")
async def get_preset_credentials(
    preset_key: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """管理端只读取凭据状态，Secret 始终保持只写。"""
    preset = await db.scalar(select(AvatarPreset).where(AvatarPreset.preset_key == preset_key))
    if not preset:
        raise HTTPException(status_code=404, detail="角色预设不存在")
    credential = _credential_for_preset(preset)
    return {
        "preset_key": preset.preset_key,
        "app_id": credential.get("app_id", ""),
        "sdk_configured": bool(credential.get("app_id") and credential.get("app_secret")),
        "secret_masked": _mask_secret(credential.get("app_secret", "")),
        "uses_legacy_credentials": not bool(preset.app_id and preset.app_secret)
        and bool(credential.get("app_id") and credential.get("app_secret")),
    }


@router.post("/presets", status_code=status.HTTP_201_CREATED)
async def create_preset(
    payload: AvatarPresetPayload,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """创建角色预设及其星云应用凭据。"""
    await _ensure_default_preset(db)
    exists = await db.scalar(select(AvatarPreset).where(AvatarPreset.preset_key == payload.preset_key))
    if exists:
        raise HTTPException(status_code=409, detail="角色预设标识已存在")
    values = payload.model_dump()
    values["app_id"], values["app_secret"] = _validate_credentials(
        values["app_id"], values["app_secret"]
    )
    preset = AvatarPreset(**values, is_active=0)
    db.add(preset)
    await db.commit()
    await db.refresh(preset)
    return _serialize(preset)


@router.put("/presets/{preset_key}")
async def update_preset(
    preset_key: str,
    payload: AvatarPresetUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    preset = await db.scalar(select(AvatarPreset).where(AvatarPreset.preset_key == preset_key))
    if not preset:
        raise HTTPException(status_code=404, detail="角色预设不存在")
    values = payload.model_dump(exclude={"clear_credentials"})
    if payload.clear_credentials:
        values["app_id"] = ""
        values["app_secret"] = ""
    else:
        submitted_app_id = (payload.app_id or "").strip()
        submitted_secret = (payload.app_secret or "").strip()
        if not submitted_app_id:
            values.pop("app_id", None)
        if not submitted_secret:
            values.pop("app_secret", None)
        effective_app_id = values.get("app_id", preset.app_id or "")
        effective_secret = values.get("app_secret", preset.app_secret or "")
        _validate_credentials(effective_app_id, effective_secret)
    for field, value in values.items():
        setattr(preset, field, value)
    await db.commit()
    await db.refresh(preset)
    return _serialize(preset)


@router.delete("/presets/{preset_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preset(
    preset_key: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """删除未启用的角色预设；默认与当前角色必须先切换后再删除。"""
    preset = await db.scalar(select(AvatarPreset).where(AvatarPreset.preset_key == preset_key))
    if not preset:
        raise HTTPException(status_code=404, detail="角色预设不存在")
    if preset.preset_key == _DEFAULT_PRESET_KEY:
        raise HTTPException(status_code=422, detail="默认讲解员预设不可删除")
    if preset.is_active:
        raise HTTPException(status_code=422, detail="请先启用其他角色后再删除当前角色")
    await db.delete(preset)
    await db.commit()


@router.post("/presets/{preset_key}/activate")
async def activate_preset(
    preset_key: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """启用已具备服务端 SDK 配置的角色预设。"""
    preset = await db.scalar(select(AvatarPreset).where(AvatarPreset.preset_key == preset_key))
    if not preset:
        raise HTTPException(status_code=404, detail="角色预设不存在")
    if not _configured(preset):
        raise HTTPException(
            status_code=422,
            detail="该角色尚未配置完整的星云应用 ID 与 Secret",
        )
    await db.execute(update(AvatarPreset).values(is_active=0))
    preset.is_active = 1
    await db.commit()
    await db.refresh(preset)
    return _serialize(preset)


@router.get("/active")
async def active_preset(response: Response, db: AsyncSession = Depends(get_db)):
    """游客端只读当前角色及会话代理地址，不返回 appSecret。"""
    preset = await _active_preset(db)
    payload = _serialize(preset, include_runtime=True, include_credential_status=False)
    payload["available"] = payload["sdk_configured"]
    payload["unavailable_reason"] = "" if payload["available"] else "当前数字人角色尚未完成服务器 SDK 配置"
    response.headers["Cache-Control"] = "no-store"
    return payload


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _xingyun_headers(method: str, target_url: str, body: dict[str, Any], app_id: str, app_secret: str) -> dict[str, str]:
    """按星云 JS SDK 同一签名规则在服务端重签请求。"""
    timestamp = str(int(time.time()))
    parsed = urlparse(target_url)
    path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    source = f"{path.lower()}{method.lower()}{_canonical_json(body).replace(' ', '')}{app_secret}{timestamp}"
    token = hashlib.md5(source.encode("utf-8")).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-APP-ID": app_id,
        "X-TOKEN": token,
        "X-TIMESTAMP": timestamp,
    }


@router.api_route("/session/{preset_key}", methods=["POST", "DELETE"])
async def proxy_avatar_session(
    preset_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """代理星云建连/销毁会话，确保切换角色后仍可用原凭据销毁旧会话。"""
    preset = await db.scalar(select(AvatarPreset).where(AvatarPreset.preset_key == preset_key))
    if not preset:
        raise HTTPException(status_code=404, detail="数字人角色不存在")
    if request.method == "POST":
        active = await _active_preset(db)
        if active.preset_key != preset_key:
            raise HTTPException(status_code=409, detail="数字人角色已更新，请重新读取角色配置后连接")
    credential = _credential_for_preset(preset)
    if not credential.get("app_id") or not credential.get("app_secret"):
        raise HTTPException(status_code=503, detail="当前数字人角色尚未完成服务器 SDK 配置")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="数字人会话请求格式无效")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="数字人会话请求格式无效")

    if request.method == "POST":
        # 角色由服务端 active preset 决定，浏览器不能传入长期密钥或覆盖预设角色配置。
        body.pop("appId", None)
        body.pop("appSecret", None)
        client_config = body.get("config") if isinstance(body.get("config"), dict) else {}
        server_config = credential.get("config") or {}
        body["config"] = {**client_config, **server_config}
        if credential.get("tag"):
            body["tag"] = credential["tag"]

    upstream = credential["gateway_url"]
    headers = _xingyun_headers(request.method, upstream, body, credential["app_id"], credential["app_secret"])
    timeout = httpx.Timeout(15.0, connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream_response = await client.request(request.method, upstream, json=body, headers=headers)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="数字人服务连接超时")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="数字人服务暂不可用")

    content_type = upstream_response.headers.get("content-type", "application/json")
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        media_type=content_type.split(";", 1)[0],
        headers={"Cache-Control": "no-store"},
    )
