"""FAQ 导入规则的共享实现。"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from app.api.knowledge import _load_faqs, _normalize_faq_term


def content_hash(item: dict[str, Any]) -> str:
    value = json.dumps(
        {
            "question": item.get("question", ""),
            "answer": item.get("answer", ""),
            "entities": item.get("entities", []),
            "intent": item.get("intent", ""),
            "intent_keywords": item.get("intent_keywords", []),
            "exact_questions": item.get("exact_questions", []),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_rows(faqs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for item in faqs:
        key = _normalize_faq_term(item.get("question", ""))
        if not key or key in seen:
            raise ValueError(f"FAQ 问题重复或为空: {item.get('question', '')}")
        seen.add(key)
        rows.append(
            {
                "question": item.get("question", "").strip(),
                "answer": item.get("answer", "").strip(),
                "match_text": item.get("match_text", ""),
                "tags": item.get("tags", []),
                "entities": item.get("entities", []),
                "intent": item.get("intent", "general_intro"),
                "intent_keywords": item.get("intent_keywords", []),
                "exact_questions": item.get("exact_questions", []),
                "normalized_question": key,
                "content_sha256": content_hash(item),
            }
        )
    return rows


def rows_to_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        **item,
        "tags": json.dumps(item["tags"], ensure_ascii=False),
        "entities": json.dumps(item["entities"], ensure_ascii=False),
        "intent_keywords": json.dumps(item["intent_keywords"], ensure_ascii=False),
        "exact_questions": json.dumps(item["exact_questions"], ensure_ascii=False),
    }


def load_default_rows() -> list[dict[str, Any]]:
    return build_rows(_load_faqs())
