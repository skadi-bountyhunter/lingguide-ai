"""active RAG 索引一致性检查的纯函数。"""
from __future__ import annotations

import hashlib
from typing import Any, Iterable


CHUNKING_CONFIG_HASH = hashlib.sha256(b"chunk_size=600;overlap=80").hexdigest()


# 必须与 shadow 索引构建时使用的字段顺序保持一致。
def canonical_fingerprint(rows: Iterable[Any]) -> str:
    """根据 canonical chunks 计算稳定指纹。"""
    digest = hashlib.sha256()
    for row in sorted(
        rows,
        key=lambda item: (str(item.document_id), item.chunk_index, str(item.id)),
    ):
        content_hash = hashlib.sha256((row.content or "").encode("utf-8")).hexdigest()
        digest.update(
            f"{row.id}\0{row.document_id}\0{row.chunk_index}\0{content_hash}\0"
            f"{row.char_start}\0{row.char_end}\n".encode("utf-8")
        )
    return digest.hexdigest()


def assess_active_index(
    manifest: Any | None,
    active: dict[str, Any],
    canonical_rows: list[Any],
    *,
    fts_available: bool,
    fts_count: int,
    vector_ids: list[str] | None,
    expected_embedding_model: str,
    expected_config_hash: str,
    check_fingerprint: bool = True,
) -> dict[str, Any]:
    """检查 active manifest 与实际三路索引是否一致，不执行任何修复。"""
    canonical_count = len(canonical_rows)
    canonical_ids = {str(row.id) for row in canonical_rows}
    canonical_hash = canonical_fingerprint(canonical_rows)
    vector_available = vector_ids is not None
    vector_count = len(vector_ids or [])
    manifest_ok = bool(
        manifest
        and manifest.state == "active"
        and manifest.version == active.get("version")
        and manifest.vector_collection == active.get("vector_collection")
        and manifest.fts_namespace == active.get("fts_namespace")
    )
    checks = {
        "manifest": manifest_ok,
        "fts": fts_available,
        "vector": vector_available,
        "counts": (
            fts_available
            and vector_available
            and canonical_count == fts_count == vector_count
        ),
        "ids": (
            vector_available
            and len(vector_ids or []) == len(canonical_ids)
            and set(vector_ids or []) == canonical_ids
        ),
        "fingerprint": (
            not check_fingerprint
            or bool(
                manifest
                and manifest.content_hash
                and manifest.content_hash == canonical_hash
            )
        ),
        "config": bool(
            manifest
            and manifest.embedding_model == expected_embedding_model
            and manifest.config_hash == expected_config_hash
        ),
    }
    return {
        "checks": checks,
        "details": {
            "canonical_count": canonical_count,
            "fts_count": int(fts_count),
            "vector_count": vector_count,
            "canonical_fingerprint": canonical_hash,
            "manifest_fingerprint": getattr(manifest, "content_hash", "") or "",
            "embedding_model": getattr(manifest, "embedding_model", "") or "",
            "expected_embedding_model": expected_embedding_model,
            "config_hash": getattr(manifest, "config_hash", "") or "",
            "expected_config_hash": expected_config_hash,
            "vector_ids_match": checks["ids"],
        },
    }
