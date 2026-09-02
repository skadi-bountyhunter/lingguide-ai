"""当前 active RAG 索引命名空间读取器。

读取失败时回退到 hybrid-v1，保证索引管理故障不会让线上问答直接中断。
"""
from __future__ import annotations

import os
import re
import sqlite3
from typing import Any

DEFAULT_INDEX = {
    "version": "hybrid-v1",
    "vector_collection": "lingguide_knowledge",
    "fts_namespace": "chunk_fts",
    "manifest_id": None,
}
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def safe_identifier(value: str, fallback: str) -> str:
    value = str(value or "")
    return value if _SAFE_IDENTIFIER.fullmatch(value) else fallback


def get_active_index(sqlite_path: str) -> dict[str, Any]:
    """从 SQLite 原子读取当前 active manifest。"""
    if not os.path.exists(sqlite_path):
        return dict(DEFAULT_INDEX)
    try:
        with sqlite3.connect(sqlite_path) as connection:
            row = connection.execute(
                "SELECT id, version, vector_collection, fts_namespace "
                "FROM index_manifests WHERE state = 'active' "
                "ORDER BY COALESCE(activated_at, created_at) DESC LIMIT 1"
            ).fetchone()
        if not row:
            return dict(DEFAULT_INDEX)
        return {
            "manifest_id": row[0],
            "version": row[1] or DEFAULT_INDEX["version"],
            "vector_collection": safe_identifier(row[2], DEFAULT_INDEX["vector_collection"]),
            "fts_namespace": safe_identifier(row[3], DEFAULT_INDEX["fts_namespace"]),
        }
    except sqlite3.Error:
        return dict(DEFAULT_INDEX)
