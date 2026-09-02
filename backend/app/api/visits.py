"""游客被动位置上报 API（景点点击热力图）"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.models import UserVisit

router = APIRouter(prefix="/api/visits", tags=["游客位置"])


class VisitCreate(BaseModel):
    spot_id: str | None = None
    lng: float
    lat: float


@router.post("", status_code=201)
async def create_visit(body: VisitCreate, db: AsyncSession = Depends(get_db)):
    visit = UserVisit(spot_id=body.spot_id, lng=body.lng, lat=body.lat)
    db.add(visit)
    await db.commit()
    return {"id": visit.id}


@router.get("/heatmap")
async def visits_heatmap(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = (await db.execute(
        select(UserVisit.lng, UserVisit.lat).where(UserVisit.created_at >= cutoff)
    )).all()
    return {
        "days": days,
        "total": len(rows),
        "points": [{"lng": r.lng, "lat": r.lat, "count": 1} for r in rows],
    }
