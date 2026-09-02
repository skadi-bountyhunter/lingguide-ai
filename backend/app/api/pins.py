"""游客自定义标记上报 API"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.models import UserPin

router = APIRouter(prefix="/api/pins", tags=["游客标记"])


class PinCreate(BaseModel):
    name: str = Field(default="", max_length=100)
    lng: float
    lat: float


@router.post("", status_code=201)
async def create_pin(body: PinCreate, db: AsyncSession = Depends(get_db)):
    pin = UserPin(name=body.name, lng=body.lng, lat=body.lat)
    db.add(pin)
    await db.commit()
    return {"id": pin.id}


@router.get("/heatmap")
async def pins_heatmap(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """返回近 N 天游客自定义标记坐标，供管理端热力图渲染。"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = (await db.execute(
        select(UserPin.lng, UserPin.lat).where(UserPin.created_at >= cutoff)
    )).all()
    return {
        "days": days,
        "total": len(rows),
        "points": [{"lng": row.lng, "lat": row.lat, "count": 1} for row in rows],
    }
