"""数据大屏服务：基于真实交互记录生成运营统计。"""
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Interaction

DashboardPeriod = Literal["today", "7d", "30d"]
_SHANGHAI = timezone(timedelta(hours=8), name="Asia/Shanghai")
_ACTIVE_WINDOW_MINUTES = 15


def _as_utc(value: datetime) -> datetime:
    """将数据库的 UTC 时间或测试传入时间标准化为带时区 UTC 时间。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _as_db_utc(value: datetime) -> datetime:
    """将带时区 UTC 时间转换为 SQLite 使用的无时区 UTC 边界。"""
    return _as_utc(value).replace(tzinfo=None)


def _format_time(value: datetime) -> str:
    """输出带中国时区偏移的 ISO 时间。"""
    return value.astimezone(_SHANGHAI).isoformat(timespec="seconds")


def _period_bounds(period: DashboardPeriod, now_utc: datetime) -> tuple[datetime, datetime, str]:
    """返回中国业务时区下的统计起止时间与趋势粒度。"""
    local_now = now_utc.astimezone(_SHANGHAI)
    local_today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "today":
        return local_today, local_now, "hour"

    days = 7 if period == "7d" else 30
    return local_today - timedelta(days=days - 1), local_now, "day"


def _bucket_starts(start: datetime, end: datetime, granularity: str) -> list[datetime]:
    """创建连续时间桶，不为尚未开始的未来时间补桶。"""
    step = timedelta(hours=1) if granularity == "hour" else timedelta(days=1)
    buckets: list[datetime] = []
    cursor = start
    while cursor < end:
        buckets.append(cursor)
        cursor += step
    return buckets


def _bucket_start(value: datetime, granularity: str) -> datetime:
    if granularity == "hour":
        return value.replace(minute=0, second=0, microsecond=0)
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def _valid_score(value: object) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return score if 0 <= score <= 1 else None


async def get_overview(
    db: AsyncSession,
    period: DashboardPeriod = "today",
    now_utc: datetime | None = None,
) -> dict:
    """按所选周期汇总真实已落库的对话交互记录。"""
    now = _as_utc(now_utc or datetime.now(timezone.utc))
    local_start, local_end, granularity = _period_bounds(period, now)
    start_db = _as_db_utc(local_start)
    end_db = _as_db_utc(now)

    result = await db.execute(
        select(
            Interaction.session_id,
            Interaction.query_text,
            Interaction.query_mode,
            Interaction.emotion_score,
            Interaction.thinking_time_ms,
            Interaction.created_at,
        ).where(
            Interaction.created_at >= start_db,
            Interaction.created_at < end_db,
        )
    )
    rows = result.all()

    session_ids: set[str] = set()
    durations: list[float] = []
    scores: list[float] = []
    questions: Counter[str] = Counter()
    mode_counts = {"text": 0, "voice": 0, "other": 0}
    active_sessions: set[str] = set()
    active_interactions = 0
    activity_start = now - timedelta(minutes=_ACTIVE_WINDOW_MINUTES)

    starts = _bucket_starts(local_start, local_end, granularity)
    bucket_counts = {bucket: 0 for bucket in starts}
    bucket_scores: dict[datetime, list[float]] = {bucket: [] for bucket in starts}

    for session_id, query_text, query_mode, emotion_score, thinking_time_ms, created_at in rows:
        if not created_at:
            continue
        created_utc = _as_utc(created_at)
        created_local = created_utc.astimezone(_SHANGHAI)

        if session_id:
            normalized_session = str(session_id).strip()
            if normalized_session:
                session_ids.add(normalized_session)
        else:
            normalized_session = ""

        if created_utc >= activity_start:
            active_interactions += 1
            if normalized_session:
                active_sessions.add(normalized_session)

        try:
            duration = float(thinking_time_ms)
        except (TypeError, ValueError):
            duration = 0
        if duration > 0:
            durations.append(duration)

        score = _valid_score(emotion_score)
        if score is not None:
            scores.append(score)

        if query_text and str(query_text).strip():
            questions[str(query_text)] += 1

        mode = str(query_mode or "").strip().lower()
        mode_counts[mode if mode in {"text", "voice"} else "other"] += 1

        start = _bucket_start(created_local, granularity)
        if start in bucket_counts:
            bucket_counts[start] += 1
            if score is not None:
                bucket_scores[start].append(score)

    total = len(rows)
    mode_items = []
    for mode in ("text", "voice", "other"):
        count = mode_counts[mode]
        mode_items.append({
            "mode": mode,
            "count": count,
            "ratio": round(count / total, 4) if total else None,
        })

    trend_buckets = []
    emotion_buckets = []
    bucket_step = timedelta(hours=1) if granularity == "hour" else timedelta(days=1)
    for start in starts:
        end = min(start + bucket_step, local_end)
        label = start.strftime("%H:00") if granularity == "hour" else start.strftime("%m-%d")
        bucket_values = bucket_scores[start]
        trend_buckets.append({
            "start": _format_time(start),
            "end": _format_time(end),
            "label": label,
            "count": bucket_counts[start],
        })
        emotion_buckets.append({
            "start": _format_time(start),
            "end": _format_time(end),
            "label": label,
            "avg_score": round(sum(bucket_values) / len(bucket_values), 4) if bucket_values else None,
            "sample_count": len(bucket_values),
        })

    ranked_questions = sorted(questions.items(), key=lambda item: (-item[1], item[0]))[:8]
    return {
        "schema_version": 1,
        "period": period,
        "timezone": "Asia/Shanghai",
        "generated_at": _format_time(now),
        "range": {
            "start": _format_time(local_start),
            "end": _format_time(local_end),
            "end_exclusive": True,
        },
        "summary": {
            "interaction_count": total,
            "session_count": len(session_ids),
            "avg_thinking_time_ms": {
                "value": round(sum(durations) / len(durations), 1) if durations else None,
                "sample_count": len(durations),
            },
            "avg_emotion_score": {
                "value": round(sum(scores) / len(scores), 4) if scores else None,
                "sample_count": len(scores),
            },
        },
        "activity": {
            "window_minutes": _ACTIVE_WINDOW_MINUTES,
            "range": {
                "start": _format_time(activity_start),
                "end": _format_time(now),
                "end_exclusive": True,
            },
            "active_session_count": len(active_sessions),
            "interaction_count": active_interactions,
        },
        "mode_distribution": {"total": total, "items": mode_items},
        "interaction_trend": {"granularity": granularity, "buckets": trend_buckets},
        "emotion_trend": {"granularity": granularity, "buckets": emotion_buckets},
        "top_questions": [
            {"question": question, "count": count}
            for question, count in ranked_questions
        ],
    }
