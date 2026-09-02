"""个人资料、收藏与游览足迹 API。"""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models import Interaction, User
from app.models.favorite import Favorite
from app.models.notification import Notification, NotificationRead
from app.models.saved_route import SavedRoute
from app.models.visit_record import VisitRecord

router = APIRouter(prefix="/api/profile", tags=["profile"])


class FavoriteCreate(BaseModel):
    """新增收藏请求。"""

    item_type: Literal["spot", "route"]
    item_id: str = Field(max_length=100)
    item_name: str = Field(max_length=200)
    item_cover: str = Field(default="", max_length=500)

    @field_validator("item_id", "item_name", "item_cover")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("item_id", "item_name")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value:
            raise ValueError("收藏对象不能为空")
        return value


class FavoriteResponse(BaseModel):
    """收藏记录响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    item_type: str
    item_id: str
    item_name: str
    item_cover: str


class ProfileUpdate(BaseModel):
    """个人资料更新请求。"""

    nickname: str = Field(min_length=1, max_length=50)

    @field_validator("nickname")
    @classmethod
    def clean_nickname(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("昵称不能为空")
        return value


class VisitCreate(BaseModel):
    """记录一次对象访问。"""

    item_type: Literal["spot", "route"] = "spot"
    item_id: str = Field(max_length=100)
    item_name: str = Field(max_length=200)
    item_cover: str = Field(default="", max_length=500)

    @field_validator("item_id", "item_name", "item_cover")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("item_id", "item_name")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value:
            raise ValueError("游览对象不能为空")
        return value


class VisitResponse(BaseModel):
    """游览足迹响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    item_type: str
    item_id: str
    item_name: str
    item_cover: str
    first_visited_at: datetime
    last_visited_at: datetime
    visit_count: int


def _visible_notifications(user_id: str):
    """构造当前用户可见通知条件。"""
    return or_(
        Notification.target_user_id.is_(None),
        Notification.target_user_id == user_id,
    )


async def _profile_payload(db: AsyncSession, user: User) -> dict:
    """汇总当前用户资料与真实统计。"""
    visits = await db.scalar(
        select(func.coalesce(func.sum(VisitRecord.visit_count), 0)).where(
            VisitRecord.user_id == user.id
        )
    )
    saved_routes = await db.scalar(
        select(func.count()).select_from(SavedRoute).where(SavedRoute.user_id == user.id)
    )
    interactions = await db.scalar(
        select(func.count()).select_from(Interaction).where(Interaction.user_id == user.id)
    )
    spot_favorites = await db.scalar(
        select(func.count()).select_from(Favorite).where(
            Favorite.user_id == user.id,
            Favorite.item_type == "spot",
        )
    )
    unread = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .outerjoin(
            NotificationRead,
            and_(
                NotificationRead.notification_id == Notification.id,
                NotificationRead.user_id == user.id,
            ),
        )
        .where(_visible_notifications(user.id), NotificationRead.id.is_(None))
    )
    phone = user.phone or ""
    masked_phone = f"{phone[:3]}****{phone[-4:]}" if len(phone) >= 7 else phone
    return {
        "id": user.id,
        "nickname": user.nickname,
        "phone": masked_phone,
        "created_at": user.created_at,
        "stats": {
            "visit_count": int(visits or 0),
            "saved_route_count": int(saved_routes or 0),
            "interaction_count": int(interactions or 0),
            "spot_favorite_count": int(spot_favorites or 0),
            "unread_notification_count": int(unread or 0),
        },
    }


@router.get("/me")
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户资料和统计。"""
    return await _profile_payload(db, current_user)


@router.patch("/me")
async def update_profile(
    data: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """仅允许当前用户修改昵称。"""
    current_user.nickname = data.nickname
    await db.commit()
    await db.refresh(current_user)
    return await _profile_payload(db, current_user)


@router.get("/favorites", response_model=list[FavoriteResponse])
async def get_favorites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户收藏列表。"""
    result = await db.execute(
        select(Favorite)
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc(), Favorite.id.desc())
    )
    return result.scalars().all()


@router.post(
    "/favorites", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED
)
async def add_favorite(
    data: FavoriteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """为当前用户添加收藏。"""
    existing = await db.scalar(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.item_type == data.item_type,
            Favorite.item_id == data.item_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=400, detail="已收藏")

    favorite = Favorite(user_id=current_user.id, **data.model_dump())
    db.add(favorite)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="已收藏") from None
    await db.refresh(favorite)
    return favorite


@router.delete("/favorites/{favorite_id}")
async def remove_favorite(
    favorite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除当前用户自己的收藏记录。"""
    favorite = await db.scalar(
        select(Favorite).where(
            Favorite.id == favorite_id,
            Favorite.user_id == current_user.id,
        )
    )
    if favorite is None:
        raise HTTPException(status_code=404, detail="收藏不存在")
    await db.delete(favorite)
    await db.commit()
    return {"deleted": favorite_id}


@router.get("/favorites/check/{item_id}")
async def check_favorite(
    item_id: str,
    item_type: Literal["spot", "route"] = Query(default="spot"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按类型和对象标识检查收藏状态。"""
    favorite = await db.scalar(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.item_type == item_type,
            Favorite.item_id == item_id,
        )
    )
    return {"favorited": favorite is not None, "id": favorite.id if favorite else None}


@router.post("/visits", response_model=VisitResponse, status_code=status.HTTP_201_CREATED)
async def record_visit(
    data: VisitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """首次创建足迹，重复访问则累加次数。"""
    visit = await db.scalar(
        select(VisitRecord).where(
            VisitRecord.user_id == current_user.id,
            VisitRecord.item_type == data.item_type,
            VisitRecord.item_id == data.item_id,
        )
    )
    if visit is None:
        visit = VisitRecord(user_id=current_user.id, **data.model_dump())
        db.add(visit)
    else:
        visit.item_name = data.item_name
        visit.item_cover = data.item_cover
        visit.last_visited_at = datetime.utcnow()
        visit.visit_count += 1
    await db.commit()
    await db.refresh(visit)
    return visit


@router.get("/visits", response_model=list[VisitResponse])
async def list_visits(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按最近访问时间倒序获取当前用户足迹。"""
    result = await db.execute(
        select(VisitRecord)
        .where(VisitRecord.user_id == current_user.id)
        .order_by(VisitRecord.last_visited_at.desc(), VisitRecord.id.desc())
    )
    return result.scalars().all()
