"""游客反馈与管理端处理 API。"""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.models import User
from app.models.feedback import Feedback

router = APIRouter(tags=["feedback"])

FeedbackCategory = Literal["suggestion", "complaint", "consultation", "praise", "other"]
FeedbackStatus = Literal["pending", "processing", "resolved", "closed"]


class FeedbackCreate(BaseModel):
    """游客反馈请求。"""

    category: FeedbackCategory = "suggestion"
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("反馈内容不能为空")
        return value


class FeedbackUpdate(BaseModel):
    """管理端处理反馈请求。"""

    status: FeedbackStatus
    admin_reply: str = Field(default="", max_length=1000)

    @field_validator("admin_reply")
    @classmethod
    def clean_reply(cls, value: str) -> str:
        return value.strip()


class FeedbackResponse(BaseModel):
    """反馈响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    content: str
    status: str
    admin_reply: str
    created_at: datetime
    updated_at: datetime


def _admin_item(feedback: Feedback, user: User | None) -> dict:
    """序列化管理端反馈及用户摘要。"""
    return {
        "id": feedback.id,
        "category": feedback.category,
        "content": feedback.content,
        "status": feedback.status,
        "admin_reply": feedback.admin_reply or "",
        "created_at": feedback.created_at,
        "updated_at": feedback.updated_at,
        "user_id": feedback.user_id,
        "user_phone": user.phone if user else "",
        "user_nickname": user.nickname if user else "",
    }


@router.post(
    "/api/profile/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feedback(
    data: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交当前用户反馈。"""
    feedback = Feedback(user_id=current_user.id, **data.model_dump())
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback


@router.get("/api/profile/feedback", response_model=list[FeedbackResponse])
async def list_feedback(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户反馈历史。"""
    result = await db.execute(
        select(Feedback)
        .where(Feedback.user_id == current_user.id)
        .order_by(Feedback.created_at.desc(), Feedback.id.desc())
    )
    return result.scalars().all()


@router.get("/api/admin/feedback")
async def list_admin_feedback(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    feedback_status: FeedbackStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _admin: User | None = Depends(require_admin),
):
    """管理员分页查看反馈。"""
    filters = [Feedback.status == feedback_status] if feedback_status else []
    total = await db.scalar(
        select(func.count()).select_from(Feedback).where(*filters)
    )
    result = await db.execute(
        select(Feedback, User)
        .outerjoin(User, User.id == Feedback.user_id)
        .where(*filters)
        .order_by(Feedback.created_at.desc(), Feedback.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "total": int(total or 0),
        "page": page,
        "page_size": page_size,
        "items": [_admin_item(feedback, user) for feedback, user in result.all()],
    }


@router.patch("/api/admin/feedback/{feedback_id}")
async def update_admin_feedback(
    feedback_id: int,
    data: FeedbackUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User | None = Depends(require_admin),
):
    """管理员更新反馈状态与回复。"""
    feedback = await db.get(Feedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="反馈不存在")
    feedback.status = data.status
    feedback.admin_reply = data.admin_reply
    feedback.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(feedback)
    return _admin_item(feedback, await db.get(User, feedback.user_id))
