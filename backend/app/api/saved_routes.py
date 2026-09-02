"""账号保存路线 API"""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models import User
from app.models.saved_route import SavedRoute

router = APIRouter(prefix="/api/profile/routes", tags=["profile"])


class SavedSpot(BaseModel):
    """路线中的景点。"""

    name: str
    description: str = ""

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class SavedRouteCreate(BaseModel):
    """保存路线请求。"""

    source: Literal["chat", "manual"] = "manual"
    title: str = Field(max_length=200)
    duration: str = Field(default="", max_length=50)
    spots: list[SavedSpot]
    tips: str = ""
    interests: list[str] = Field(default_factory=list)
    citations: list[dict] = Field(default_factory=list)
    retrieval: dict = Field(default_factory=dict)
    trace_id: str = ""
    traceId: str = ""
    index_version: str = ""

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("路线标题不能为空")
        return value

    @field_validator("duration", "tips")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("spots")
    @classmethod
    def validate_spots(cls, value: list[SavedSpot]) -> list[SavedSpot]:
        spots = [spot for spot in value if spot.name]
        if not spots:
            raise ValueError("至少需要一个景点")
        return spots

    @field_validator("interests")
    @classmethod
    def clean_interests(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class SavedRouteResponse(BaseModel):
    """保存路线响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    title: str
    duration: str
    spots: list[SavedSpot]
    tips: str
    interests: list[str]
    citations: list[dict] = []
    retrieval: dict = {}
    trace_id: str = ""
    index_version: str = ""
    created_at: datetime


def _json_list(value: str | None) -> list:
    import json
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def _json_dict(value: str | None) -> dict:
    import json
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _to_response(route: SavedRoute) -> SavedRouteResponse:
    """将数据库模型转换为响应。"""
    return SavedRouteResponse(
        id=route.id,
        source=route.source,
        title=route.title,
        duration=route.duration or "",
        spots=route.spots_list,
        tips=route.tips or "",
        interests=route.interests_list,
        citations=_json_list(route.citations),
        retrieval=_json_dict(route.retrieval),
        trace_id=route.trace_id or "",
        index_version=route.index_version or "",
        created_at=route.created_at,
    )


@router.get("", response_model=list[SavedRouteResponse], response_model_exclude_defaults=True)
async def list_saved_routes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按创建时间倒序获取当前用户路线。"""
    result = await db.execute(
        select(SavedRoute)
        .where(SavedRoute.user_id == current_user.id)
        .order_by(SavedRoute.created_at.desc(), SavedRoute.id.desc())
    )
    return [_to_response(route) for route in result.scalars().all()]


@router.post("", response_model=SavedRouteResponse, response_model_exclude_defaults=True, status_code=status.HTTP_201_CREATED)
async def create_saved_route(
    data: SavedRouteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """为当前用户保存路线。"""
    route = SavedRoute(
        user_id=current_user.id,
        source=data.source,
        title=data.title,
        duration=data.duration,
        tips=data.tips,
    )
    route.spots_list = [spot.model_dump() for spot in data.spots]
    route.interests_list = data.interests
    import json
    route.citations = json.dumps(data.citations, ensure_ascii=False)
    route.retrieval = json.dumps(data.retrieval, ensure_ascii=False)
    route.trace_id = data.trace_id or data.traceId
    route.index_version = data.index_version
    db.add(route)
    await db.commit()
    await db.refresh(route)
    return _to_response(route)


@router.delete("/{route_id}")
async def delete_saved_route(
    route_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除当前用户自己的路线。"""
    result = await db.execute(
        select(SavedRoute).where(
            SavedRoute.id == route_id,
            SavedRoute.user_id == current_user.id,
        )
    )
    route = result.scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="路线不存在")

    await db.delete(route)
    await db.commit()
    return {"deleted": route_id}
