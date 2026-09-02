"""从 SQLite 结构化景点和路线表召回可核验 Evidence。"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from app.config import resolve_runtime_path, settings
from app.core.retrieval_types import RAGResult


_ROUTE_TERMS = ("路线", "规划", "顺序", "怎么走", "游览", "行程", "半天", "全天", "一日游")


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def _json_list(value: Any) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, ValueError):
        return []
    return [str(item) for item in parsed if item]


def _query_terms(query: str) -> list[str]:
    text = _normalize(query)
    if not text:
        return []
    terms = [text]
    terms.extend(text[index:index + 2] for index in range(max(0, len(text) - 1)))
    return list(dict.fromkeys(item for item in terms if item))


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class StructuredRetriever:
    """只读读取 Spot/Route canonical 数据，不维护第二份索引。"""

    def __init__(self, sqlite_path: str | None = None):
        self.sqlite_path = resolve_runtime_path(sqlite_path or settings.sqlite_path)

    @staticmethod
    def _score(query: str, name: str, fields: list[str], *, route: bool) -> float:
        text = _normalize(query)
        normalized_name = _normalize(name)
        if not text or not normalized_name:
            return 0.0
        score = 0.0
        if normalized_name in text:
            score += 100.0
        elif text in normalized_name:
            score += 70.0
        terms = _query_terms(query)
        searchable = _normalize(" ".join(fields))
        score += sum(1.0 for term in terms if len(term) > 1 and term in searchable)
        if route and any(term in text for term in _ROUTE_TERMS):
            score += 8.0
        return score

    def search(self, query: str, top_k: int = 30) -> list[RAGResult]:
        if not Path(self.sqlite_path).exists():
            return []
        try:
            with sqlite3.connect(self.sqlite_path) as connection:
                spots = connection.execute(
                    "SELECT id, name, desc, full_desc, tags, highlights, hours, ticket, tips, nearby "
                    "FROM spots ORDER BY sort_order ASC, id ASC"
                ).fetchall()
                routes = connection.execute(
                    "SELECT id, title, duration, distance, difficulty, desc, spots, tags, tip "
                    "FROM routes ORDER BY sort_order ASC, id ASC"
                ).fetchall()
        except sqlite3.Error:
            return []

        candidates: list[tuple[float, str, RAGResult]] = []
        for row in spots:
            spot_id, name, desc, full_desc, tags, highlights, hours, ticket, tips, nearby = row
            fields = [
                str(desc or ""), str(full_desc or ""),
                " ".join(_json_list(tags) + _json_list(highlights) + _json_list(tips) + _json_list(nearby)),
                str(hours or ""), str(ticket or ""),
            ]
            score = self._score(query, str(name), fields, route=False)
            if score <= 0:
                continue
            content = str(full_desc or desc or "").strip()
            if not content:
                continue
            key = f"spot:{spot_id}"
            candidates.append((score, key, RAGResult(
                content=content,
                source=str(name),
                score=score,
                chunk_id=key,
                document_id=key,
                source_type="spot",
                retrieval_method="structured_spot",
                content_hash=_content_hash(content),
                index_version="spot-live",
                confidence=1.0,
                quality_reason="structured_spot_match",
                status="ready",
                metadata={"spot_id": int(spot_id), "tags": _json_list(tags)},
            )))

        for row in routes:
            route_id, title, duration, distance, difficulty, desc, spots, tags, tip = row
            fields = [
                str(duration or ""), str(distance or ""), str(difficulty or ""),
                str(desc or ""), " ".join(_json_list(spots) + _json_list(tags)), str(tip or ""),
            ]
            score = self._score(query, str(title), fields, route=True)
            if score <= 0:
                continue
            content = "\n".join(item for item in [
                str(desc or "").strip(),
                f"游览时长：{duration}" if duration else "",
                f"包含景点：{'、'.join(_json_list(spots))}" if spots else "",
                f"提示：{tip}" if tip else "",
            ] if item)
            if not content:
                continue
            key = f"route:{route_id}"
            candidates.append((score, key, RAGResult(
                content=content,
                source=str(title),
                score=score,
                chunk_id=key,
                document_id=key,
                source_type="route",
                retrieval_method="structured_route",
                content_hash=_content_hash(content),
                index_version="route-live",
                confidence=1.0,
                quality_reason="structured_route_match",
                status="ready",
                metadata={"route_id": int(route_id), "spots": _json_list(spots)},
            )))

        candidates.sort(key=lambda item: (-item[0], item[1]))
        output = []
        for rank, (score, _, result) in enumerate(candidates[:top_k], 1):
            result.rank = rank
            result.score = round(score, 6)
            result.fused_score = round(1.0 / (60 + rank), 6)
            output.append(result)
        return output


structured_retriever = StructuredRetriever()
