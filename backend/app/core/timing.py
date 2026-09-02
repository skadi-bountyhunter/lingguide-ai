"""低开销、无共享状态的单调时钟工具。"""
from __future__ import annotations

import time


def started() -> float:
    """返回单调计时起点。"""
    return time.perf_counter()


def elapsed_ms(started_at: float) -> int:
    """返回非负整数毫秒，适合写入低敏诊断字段。"""
    return max(0, int((time.perf_counter() - started_at) * 1000))
