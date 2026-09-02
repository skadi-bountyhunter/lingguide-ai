"""游客通知、管理端发布与进程内实时推送。"""
import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_admin, resolve_user_token
from app.config import settings
from app.core.database import async_session, get_db
from app.models import User
from app.models.notification import Notification, NotificationRead

router = APIRouter(tags=["notifications"])
NotificationCategory = Literal["system", "activity", "service", "alert"]


class NotificationCreate(BaseModel):
    """管理端发布通知请求。"""

    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=2000)
    category: NotificationCategory = "system"
    target_user_id: str | None = None

    @field_validator("title", "content")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("通知标题和内容不能为空")
        return value

    @field_validator("target_user_id")
    @classmethod
    def clean_target(cls, value: str | None) -> str | None:
        value = value.strip() if value else ""
        return value or None


class NotificationConnectionManager:
    """单进程通知连接管理器。"""

    def __init__(self) -> None:
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)
        self.lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        async with self.lock:
            self.connections[user_id].add(websocket)

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        async with self.lock:
            sockets = self.connections.get(user_id)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self.connections.pop(user_id, None)

    async def target_users(self, target_user_id: str | None) -> list[str]:
        async with self.lock:
            if target_user_id:
                return [target_user_id] if target_user_id in self.connections else []
            return list(self.connections)

    async def send(self, user_id: str, payload: dict) -> None:
        async with self.lock:
            sockets = list(self.connections.get(user_id, ()))
        failed = []
        for websocket in sockets:
            try:
                await websocket.send_json(payload)
            except Exception:
                failed.append(websocket)
        for websocket in failed:
            await self.disconnect(user_id, websocket)


notification_manager = NotificationConnectionManager()


def _visible(user_id: str):
    """当前用户可见全体通知和个人通知。"""
    return or_(
        Notification.target_user_id.is_(None),
        Notification.target_user_id == user_id,
    )


def _item(notification: Notification, *, is_read: bool = False) -> dict:
    """序列化通知。"""
    return {
        "id": notification.id,
        "title": notification.title,
        "content": notification.content,
        "category": notification.category,
        "target_user_id": notification.target_user_id,
        "created_by": notification.created_by,
        "created_at": notification.created_at,
        "is_read": is_read,
    }


async def _unread_count(db: AsyncSession, user_id: str) -> int:
    """统计当前用户可见且未读的通知。"""
    count = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .outerjoin(
            NotificationRead,
            and_(
                NotificationRead.notification_id == Notification.id,
                NotificationRead.user_id == user_id,
            ),
        )
        .where(_visible(user_id), NotificationRead.id.is_(None))
    )
    return int(count or 0)


@router.get("/api/profile/notifications")
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户可见通知及独立已读状态。"""
    result = await db.execute(
        select(Notification, NotificationRead.id)
        .outerjoin(
            NotificationRead,
            and_(
                NotificationRead.notification_id == Notification.id,
                NotificationRead.user_id == current_user.id,
            ),
        )
        .where(_visible(current_user.id))
        .order_by(Notification.created_at.desc(), Notification.id.desc())
    )
    return [
        _item(notification, is_read=read_id is not None)
        for notification, read_id in result.all()
    ]


@router.get("/api/profile/notifications/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户未读通知数。"""
    return {"unread_count": await _unread_count(db, current_user.id)}


@router.patch("/api/profile/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记当前用户可见通知为已读。"""
    notification = await db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            _visible(current_user.id),
        )
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="通知不存在")
    existing = await db.scalar(
        select(NotificationRead).where(
            NotificationRead.notification_id == notification_id,
            NotificationRead.user_id == current_user.id,
        )
    )
    if existing is None:
        db.add(
            NotificationRead(
                notification_id=notification_id,
                user_id=current_user.id,
            )
        )
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
    return {
        "id": notification_id,
        "is_read": True,
        "unread_count": await _unread_count(db, current_user.id),
    }


@router.get("/api/admin/notifications")
async def list_admin_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User | None = Depends(require_admin),
):
    """管理员分页查看已发布通知。"""
    total = await db.scalar(select(func.count()).select_from(Notification))
    result = await db.execute(
        select(Notification, User)
        .outerjoin(User, User.id == Notification.target_user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for notification, target_user in result.all():
        item = _item(notification)
        item.update(
            {
                "target_user_phone": target_user.phone if target_user else "",
                "target_user_nickname": target_user.nickname if target_user else "",
            }
        )
        items.append(item)
    return {
        "total": int(total or 0),
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.post("/api/admin/notifications", status_code=201)
async def create_notification(
    data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    admin: User | None = Depends(require_admin),
):
    """管理员发布通知并推送至当前进程在线用户。"""
    if data.target_user_id and await db.get(User, data.target_user_id) is None:
        raise HTTPException(status_code=404, detail="目标用户不存在")
    notification = Notification(
        **data.model_dump(),
        created_by=admin.id if admin else None,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    for user_id in await notification_manager.target_users(notification.target_user_id):
        await notification_manager.send(
            user_id,
            {
                "type": "notification_created",
                "notification": _item(notification),
                "unread_count": await _unread_count(db, user_id),
            },
        )
    return _item(notification)


@router.websocket("/api/profile/notifications/ws")
async def notifications_websocket(websocket: WebSocket):
    """首帧校验账号 token 后订阅实时通知。"""
    await websocket.accept()
    user_id = ""
    try:
        first = await asyncio.wait_for(
            websocket.receive_json(), timeout=settings.websocket_receive_timeout_seconds
        )
        token = str(first.get("auth_token", first.get("token", ""))).strip()
        async with async_session() as db:
            user = await resolve_user_token(token, db)
        user_id = user.id
        await notification_manager.connect(user_id, websocket)
        await websocket.send_json({"type": "connected", "user_id": user_id})
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    except HTTPException:
        await websocket.close(code=1008, reason="认证失败")
    finally:
        if user_id:
            await notification_manager.disconnect(user_id, websocket)
