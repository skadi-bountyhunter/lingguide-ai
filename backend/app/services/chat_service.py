"""对话服务 — 交互记录存储与统计"""
import json
from datetime import datetime
from sqlalchemy import select, func
from app.core.database import get_db
from app.models import Interaction


# 测试或隔离运行时可替换；生产默认仍使用全局数据库依赖。
db_provider = get_db
from loguru import logger


async def log_interaction(
    session_id: str,
    query_text: str,
    response_text: str,
    query_mode: str = "text",
    user_id: str | None = None,
    rag_sources: list | None = None,
    emotion_label: str = "neutral",
    emotion_score: float = 0.5,
    thinking_time_ms: int = 0,
    citations: list | None = None,
    retrieval: dict | None = None,
    trace_id: str = "",
    spot_id: str | None = None,
):
    """记录一次对话交互"""
    import uuid
    try:
        async for db in db_provider():
            interaction = Interaction(
                id=uuid.uuid4().hex,
                session_id=session_id,
                user_id=user_id,
                query_text=query_text,
                query_mode=query_mode,
                response_text=response_text,
                rag_sources=json.dumps(rag_sources or [], ensure_ascii=False),
                emotion_label=emotion_label,
                emotion_score=emotion_score,
                spot_id=spot_id,
                thinking_time_ms=thinking_time_ms,
                citations_json=json.dumps(citations or [], ensure_ascii=False),
                retrieval_json=json.dumps(retrieval or {}, ensure_ascii=False),
                trace_id=trace_id,
            )
            db.add(interaction)
            await db.commit()
    except Exception as e:
        logger.warning(f"交互日志写入失败: {e}")


async def get_session_history(
    session_id: str,
    limit: int = 6,
    user_id: str | None = None,
) -> list[dict]:
    """获取会话历史；登录用户额外按账号隔离，匿名仅读取匿名记录。"""
    if not session_id:
        return []
    try:
        async for db in db_provider():
            owner_filter = (
                Interaction.user_id == user_id
                if user_id is not None
                else Interaction.user_id.is_(None)
            )
            stmt = (
                select(Interaction)
                .where(Interaction.session_id == session_id, owner_filter)
                .order_by(Interaction.created_at.desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            rows = list(reversed(result.scalars().all()))
            return [
                {
                    "query_text": (r.query_text or "")[:120],
                    "response_text": (r.response_text or "")[:180],
                }
                for r in rows
            ]
    except Exception as e:
        logger.warning(f"会话历史读取失败: {e}")
        return []


def build_history_context(history: list[dict]) -> str:
    """把历史对话压缩成 prompt 片段，避免无限膨胀上下文"""
    if not history:
        return ""
    parts = []
    for item in history:
        query = item.get("query_text", "").strip()
        reply = item.get("response_text", "").strip()
        if query:
            parts.append(f"游客：{query}")
        if reply:
            parts.append(f"小灵：{reply}")
    return "\n".join(parts)


async def get_recent_interactions(days: int = 7) -> list[dict]:
    """获取近 N 天的交互记录"""
    try:
        async for db in db_provider():
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(days=days)
            stmt = (
                select(Interaction)
                .where(Interaction.created_at >= since)
                .order_by(Interaction.created_at.desc())
                .limit(500)
            )
            result = await db.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "query_text": r.query_text,
                    "query_mode": r.query_mode,
                    "emotion_label": r.emotion_label,
                    "emotion_score": r.emotion_score,
                    "thinking_time_ms": r.thinking_time_ms,
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                }
                for r in rows
            ]
    except Exception:
        return []


async def get_interaction_count(days: int = 7) -> int:
    """获取近 N 天的交互总数"""
    try:
        async for db in db_provider():
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(days=days)
            stmt = select(func.count()).where(Interaction.created_at >= since)
            result = await db.execute(stmt)
            return result.scalar() or 0
    except Exception:
        return 0
