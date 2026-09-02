"""数据大屏 API：基于真实交互记录的运营统计。"""
from typing import Literal

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.services.dashboard_service import get_overview

router = APIRouter(prefix="/api/dashboard", tags=["数据大屏"])


@router.get("/overview")
async def dashboard_overview(
    response: Response,
    period: Literal["today", "7d", "30d"] = "today",
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """返回指定中国业务周期内真实落库交互的运营统计。"""
    response.headers["Cache-Control"] = "no-store"
    return await get_overview(db, period)
