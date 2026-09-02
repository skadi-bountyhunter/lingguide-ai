"""受控演示环境的 RAG 索引初始化命令。

该命令只使用已有 canonical 文档构建 shadow 索引，不删除旧的 FTS 或 Chroma 数据。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select

# 支持从 backend/tools/init_demo.py 直接运行。
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import resolve_runtime_path, settings  # noqa: E402
from app.core.database import (  # noqa: E402
    Base,
    async_session,
    build_runtime,
    init_db,
)
from app.core.index_readiness import (  # noqa: E402
    CHUNKING_CONFIG_HASH,
    assess_active_index,
    canonical_fingerprint,
)
from app.core.index_runtime import get_active_index  # noqa: E402
from app.core.rag import SQLiteLexicalRetriever  # noqa: E402
from app.models import Chunk, Document, FAQ, IndexManifest  # noqa: E402
from app.services.index_lifecycle import IndexLifecycleService  # noqa: E402


class DemoInitError(RuntimeError):
    """演示初始化失败，调用方应以非零状态退出。"""


async def _canonical_rows(db) -> list[Chunk]:
    rows = (
        await db.execute(
            select(Chunk)
            .join(Document, Document.id == Chunk.document_id)
            .where(Chunk.status == "ready", Document.status == "ready")
            .order_by(Chunk.document_id, Chunk.chunk_index, Chunk.id)
        )
    ).scalars().all()
    return list(rows)


def _schema_tables(sqlite_path: str) -> set[str]:
    if not Path(sqlite_path).is_file():
        return set()
    with sqlite3.connect(sqlite_path) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }


def _ensure_lifecycle_schema(sqlite_path: str) -> None:
    missing = {"index_manifests", "index_jobs"} - _schema_tables(sqlite_path)
    if missing:
        raise DemoInitError(f"数据库缺少索引生命周期表: {','.join(sorted(missing))}")


def _load_faq_source(path: str) -> list[dict[str, Any]]:
    from app.tools_faq import build_rows

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DemoInitError(f"FAQ 文件读取失败: {type(exc).__name__}") from exc
    if not isinstance(payload, list):
        raise DemoInitError("FAQ 文件必须是 JSON 数组")
    return build_rows(payload)


async def _sync_faqs(db, source: str) -> dict[str, int]:
    """复用 FAQ 标准化规则，幂等写入 SQLite。"""
    from app.tools_faq import rows_to_payload

    rows = _load_faq_source(source)
    existing = {
        row.normalized_question: row
        for row in (await db.execute(select(FAQ))).scalars().all()
    }
    inserted = updated = 0
    for item in rows:
        payload = rows_to_payload(item)
        row = existing.get(item["normalized_question"])
        if row is None:
            db.add(FAQ(**payload))
            inserted += 1
        elif row.content_sha256 != item["content_sha256"]:
            for key, value in payload.items():
                setattr(row, key, value)
            updated += 1
    await db.commit()
    return {"source_count": len(rows), "inserted": inserted, "updated": updated}


async def _readiness_report(db, lifecycle: IndexLifecycleService) -> dict[str, Any]:
    """使用与 HTTP readiness 相同的纯函数检查 active 三路索引。"""
    active = get_active_index(lifecycle.sqlite_path)
    manifest = None
    if active.get("manifest_id"):
        manifest = await db.scalar(
            select(IndexManifest).where(IndexManifest.id == active["manifest_id"])
        )
    rows = await _canonical_rows(db)
    fts_available = False
    fts_count = 0
    try:
        with sqlite3.connect(lifecycle.sqlite_path) as connection:
            fts_available = bool(
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (active["fts_namespace"],),
                ).fetchone()
            )
            if fts_available:
                fts_count = int(
                    connection.execute(
                        f"SELECT COUNT(*) FROM {active['fts_namespace']}"
                    ).fetchone()[0]
                )
    except sqlite3.Error:
        fts_available = False

    vector_ids = None
    if manifest:
        try:
            vector_ids = lifecycle._vector_ids(manifest)
        except Exception:
            vector_ids = None
    report = assess_active_index(
        manifest,
        active,
        rows,
        fts_available=fts_available,
        fts_count=fts_count,
        vector_ids=vector_ids,
        expected_embedding_model=settings.embedding_model,
        expected_config_hash=CHUNKING_CONFIG_HASH,
    )
    return {
        "status": "ready" if all(report["checks"].values()) else "not_ready",
        "checks": report["checks"],
        "details": {
            **report["details"],
            "index_version": active.get("version"),
            "manifest_id": active.get("manifest_id"),
        },
    }


def _stable_key(rows: list[Chunk], explicit: str | None, rebuild: bool) -> str:
    if explicit:
        return explicit
    fingerprint = canonical_fingerprint(rows)
    suffix = ":rebuild" if rebuild else ""
    return f"demo-index:{fingerprint}:{settings.embedding_model}:{CHUNKING_CONFIG_HASH}{suffix}"


async def initialize_demo(
    *,
    sqlite_path: str | None = None,
    chroma_path: str | None = None,
    idempotency_key: str | None = None,
    sync_faqs: bool = False,
    faq_source: str | None = None,
    rebuild: bool = False,
    activate: bool = True,
    dry_run: bool = False,
    embedder=None,
) -> dict[str, Any]:
    """执行一次可复现的演示索引初始化。"""
    resolved_sqlite = resolve_runtime_path(sqlite_path or settings.sqlite_path)
    resolved_chroma = resolve_runtime_path(chroma_path or settings.chroma_path)
    default_sqlite = resolved_sqlite == resolve_runtime_path(settings.sqlite_path)
    runtime_engine = None

    if dry_run:
        if not Path(resolved_sqlite).is_file():
            raise DemoInitError(f"SQLite 文件不存在: {resolved_sqlite}")
        session_factory = async_session if default_sqlite else build_runtime(resolved_sqlite)[1]
    elif default_sqlite:
        await init_db()
        session_factory = async_session
    else:
        runtime_engine, session_factory = build_runtime(resolved_sqlite)
        async with runtime_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        SQLiteLexicalRetriever(resolved_sqlite, ensure_schema=True)

    try:
        _ensure_lifecycle_schema(resolved_sqlite)
        lifecycle = IndexLifecycleService(
            sqlite_path=resolved_sqlite,
            chroma_path=resolved_chroma,
            embedder=embedder,
        )
        async with session_factory() as db:
            rows = await _canonical_rows(db)
            if not rows:
                raise DemoInitError("没有 ready canonical chunks，禁止生成空演示索引")
            fingerprint = canonical_fingerprint(rows)
            result: dict[str, Any] = {
                "sqlite": resolved_sqlite,
                "chroma": resolved_chroma,
                "canonical_chunks": len(rows),
                "canonical_fingerprint": fingerprint,
                "dry_run": dry_run,
            }

            if sync_faqs:
                if dry_run:
                    result["faq"] = {"dry_run": True, "source": faq_source or "default"}
                else:
                    result["faq"] = await _sync_faqs(
                        db,
                        resolve_runtime_path(faq_source or str(BACKEND_ROOT / "app" / "faqs.json")),
                    )

            before = await _readiness_report(db, lifecycle)
            if before["status"] == "ready" and before["details"].get("canonical_fingerprint") == fingerprint:
                result.update({"action": "already_ready", "readiness": before})
                return result
            if dry_run:
                result.update({"action": "would_build", "readiness": before})
                return result

            key = _stable_key(rows, idempotency_key, rebuild)
            job = await lifecycle.create_job(db, job_type="rebuild", idempotency_key=key)
            manifest = await db.scalar(
                select(IndexManifest).where(IndexManifest.version == job.target_version)
            )
            if job.state == "failed" and not rebuild:
                raise DemoInitError("同一幂等任务已失败；如需重建请显式传入 --rebuild")
            if job.state != "succeeded":
                outcome = await lifecycle.run_job(db, job.id, owner="demo-init")
                result["job"] = outcome
            else:
                result["job"] = {"job_id": job.id, "state": job.state}

            manifest = await db.scalar(
                select(IndexManifest).where(IndexManifest.version == job.target_version)
            )
            if not manifest or manifest.state != "validated":
                raise DemoInitError("shadow 索引未通过校验，禁止激活")
            if activate:
                manifest = await lifecycle.activate(db, manifest.version)
                result["manifest"] = {
                    "id": manifest.id,
                    "version": manifest.version,
                    "state": manifest.state,
                }
            else:
                result["manifest"] = {
                    "id": manifest.id,
                    "version": manifest.version,
                    "state": manifest.state,
                }
            result["readiness"] = await _readiness_report(db, lifecycle)
            if activate and result["readiness"]["status"] != "ready":
                raise DemoInitError("激活后 readiness 仍未就绪")
            return result
    finally:
        if runtime_engine is not None:
            await runtime_engine.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="初始化受控演示环境的 shadow RAG 索引")
    parser.add_argument("--sqlite", help="SQLite 路径，默认使用应用配置")
    parser.add_argument("--chroma", help="Chroma 路径，默认使用应用配置")
    parser.add_argument("--idempotency-key", help="覆盖自动生成的稳定幂等键")
    parser.add_argument("--sync-faqs", action="store_true", help="显式同步 FAQ JSON 到 SQLite")
    parser.add_argument("--faq-source", help="FAQ JSON 路径")
    parser.add_argument("--rebuild", action="store_true", help="允许为新 canonical 指纹创建新 shadow 版本")
    parser.add_argument("--no-activate", dest="activate", action="store_false", help="只构建并校验，不切换 active")
    parser.add_argument("--dry-run", action="store_true", help="只读检查，不创建任务或写入索引")
    parser.add_argument("--json", action="store_true", help="仅输出 JSON 结果")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = asyncio.run(
            initialize_demo(
                sqlite_path=args.sqlite,
                chroma_path=args.chroma,
                idempotency_key=args.idempotency_key,
                sync_faqs=args.sync_faqs,
                faq_source=args.faq_source,
                rebuild=args.rebuild,
                activate=args.activate,
                dry_run=args.dry_run,
            )
        )
    except DemoInitError as exc:
        payload = {"status": "failed", "error": str(exc)}
        print(json.dumps(payload, ensure_ascii=False) if args.json else f"初始化失败：{exc}")
        return 1
    except Exception as exc:  # 不输出可能包含配置值的异常正文
        payload = {"status": "failed", "error": type(exc).__name__}
        print(json.dumps(payload, ensure_ascii=False) if args.json else f"初始化失败：{type(exc).__name__}")
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
