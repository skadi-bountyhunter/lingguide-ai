"""用户认证 API — SQLite 持久化"""
import random
import secrets

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.core.database import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["认证"])

# 验证码与桌面会话均只保存在进程内，重启即失效。
_verify_codes: dict[str, str] = {}  # phone → code
_desktop_sessions: dict[str, str] = {}  # 随机 token → user_id
_DESKTOP_PHONE = "00000000000"


class LoginRequest(BaseModel):
    phone: str
    password: str


class RegisterRequest(BaseModel):
    phone: str
    password: str
    verify_code: str = ""


class ResetPasswordRequest(BaseModel):
    """开发模式验证码重置密码请求。"""

    phone: str
    verify_code: str
    new_password: str


def resolve_desktop_session(token: str) -> str | None:
    """解析进程内桌面会话，不持久化也不记录 token。"""
    return _desktop_sessions.get(token)


@router.post("/desktop-login")
async def desktop_login(db: AsyncSession = Depends(get_db)):
    """便携版一键登录，返回前端兼容的随机本机会话。"""
    if not settings.is_desktop:
        raise HTTPException(404, "接口不存在")
    user = await db.scalar(select(User).where(User.phone == _DESKTOP_PHONE))
    if user is None:
        user = User(
            phone=_DESKTOP_PHONE,
            password=secrets.token_urlsafe(32),
            nickname="本机游客",
            role="visitor",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    token = secrets.token_urlsafe(48)
    _desktop_sessions[token] = user.id
    return {
        "token": token,
        "user": {"phone": user.phone, "nickname": user.nickname},
    }


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """手机号+密码登录"""
    stmt = select(User).where(User.phone == req.phone)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(401, "该手机号未注册")
    if user.password != req.password:
        raise HTTPException(401, "密码错误")
    return {"token": f"token_{req.phone}", "user": {"phone": user.phone, "nickname": user.nickname}}


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """手机号注册"""
    # 校验手机号
    stmt = select(User).where(User.phone == req.phone)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(409, "该手机号已注册")
    if len(req.phone) != 11:
        raise HTTPException(400, "请输入正确的11位手机号")
    if len(req.password) < 6:
        raise HTTPException(400, "密码至少6位")
    # 校验验证码
    stored = _verify_codes.get(req.phone)
    if req.verify_code == "000000":
        pass  # 万能开发码
    elif stored and req.verify_code == stored:
        pass
    else:
        raise HTTPException(400, f"验证码错误，应为 {stored}" if stored else "请先获取验证码")
    # 写入数据库
    import uuid
    user = User(
        id=uuid.uuid4().hex,
        phone=req.phone,
        password=req.password,
        nickname=f"游客{req.phone[-4:]}",
    )
    db.add(user)
    await db.commit()
    _verify_codes.pop(req.phone, None)
    return {"token": f"token_{req.phone}", "user": {"phone": user.phone, "nickname": user.nickname}}


@router.post("/reset-password")
async def reset_password(
    req: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """校验一次性验证码后更新现有兼容密码字段。"""
    if len(req.phone) != 11:
        raise HTTPException(400, "请输入正确的11位手机号")
    if len(req.new_password) < 6:
        raise HTTPException(400, "密码至少6位")
    user = await db.scalar(select(User).where(User.phone == req.phone))
    if user is None:
        raise HTTPException(404, "该手机号未注册")
    stored = _verify_codes.get(req.phone)
    if not stored or req.verify_code != stored:
        raise HTTPException(400, "验证码错误或已失效")
    user.password = req.new_password
    await db.commit()
    _verify_codes.pop(req.phone, None)
    return {"message": "密码重置成功"}


@router.post("/send-code")
async def send_code(phone: str = Query(..., description="手机号")):
    """发送验证码（开发模式：返回明文）"""
    if len(phone) != 11:
        raise HTTPException(400, "请输入正确的11位手机号")
    code = f"{random.randint(100000, 999999)}"
    _verify_codes[phone] = code
    return {"code": code, "message": f"验证码已生成（开发模式），您的验证码是：{code}"}
