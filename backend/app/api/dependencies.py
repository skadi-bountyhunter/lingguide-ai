"""API 公共依赖。"""
import hmac

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.models import User


def _extract_token(authorization: str | None) -> str:
    """兼容原始 token 与 Bearer token。"""
    value = authorization.strip() if authorization else ""
    parts = value.split()
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return ""


async def resolve_user_token(token_value: str, db: AsyncSession) -> User:
    """校验 token 并查询真实用户，供 HTTP 与 WebSocket 共用。"""
    token = _extract_token(token_value)
    if settings.is_desktop:
        from app.api.auth import resolve_desktop_session

        user_id = resolve_desktop_session(token)
        if user_id:
            user = await db.get(User, user_id)
            if user is not None:
                return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
        )
    if not token.startswith("token_") or not token.removeprefix("token_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
        )
    result = await db.execute(
        select(User).where(User.phone == token.removeprefix("token_"))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
        )
    return user


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """查询当前登录用户。"""
    return await resolve_user_token(authorization or "", db)


async def get_optional_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """缺少凭证时返回匿名，有无效凭证时拒绝请求。"""
    if not authorization or not authorization.strip():
        return None
    return await resolve_user_token(authorization, db)


async def require_admin(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """限制管理端接口；仅开发调试模式保留无凭证兼容。"""
    token = _extract_token(authorization)
    if settings.is_desktop and settings.admin_token:
        if hmac.compare_digest(token, settings.admin_token):
            return None
    if settings.runtime_mode == "development" and settings.app_debug and not authorization:
        return None
    return await _require_admin_user(authorization, db)


async def _require_admin_user(
    authorization: str | None,
    db: AsyncSession,
) -> User:
    """校验管理员角色。"""
    user = await resolve_user_token(authorization or "", db)
    if user.role not in {"admin", "operator"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user
