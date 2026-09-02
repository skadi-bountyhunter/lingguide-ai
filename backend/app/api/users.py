"""用户管理 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import require_admin
from app.core.database import get_db
from app.models import User

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """用户列表（分页）"""
    # 总数
    count_stmt = select(func.count()).select_from(User)
    result = await db.execute(count_stmt)
    total = result.scalar() or 0

    # 分页查询
    stmt = select(User).order_by(User.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": u.id,
                "phone": u.phone,
                "nickname": u.nickname,
                "created_at": u.created_at.isoformat() if u.created_at else "",
            }
            for u in users
        ],
    }
