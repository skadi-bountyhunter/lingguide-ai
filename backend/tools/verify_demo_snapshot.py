"""只读校验冻结的演示知识库、FAQ 和 active 索引。"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import resolve_runtime_path, settings
from app.core.index_readiness import CHUNKING_CONFIG_HASH, assess_active_index
from app.core.index_runtime import get_active_index
from app.core.rag import SQLiteLexicalRetriever
from sqlalchemy import select

from app.core.database import async_session, build_runtime
from app.models import Chunk, Document, FAQ, IndexManifest
from app.tools_faq import build_rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def verify_snapshot(
    manifest_path: str | Path,
    *,
    sqlite_path: str | None = None,
    chroma_path: str | None = None,
    faq_path: str | None = None,
) -> dict[str, Any]:
    """读取冻结清单并验证演示运行时，不写入 SQLite、Chroma 或 FAQ。"""
    spec = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    sqlite_value = resolve_runtime_path(sqlite_path or settings.sqlite_path)
    chroma_value = resolve_runtime_path(chroma_path or settings.chroma_path)
    faq_value = Path(resolve_runtime_path(faq_path or str(ROOT / "app" / "faqs.json")))
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {"sqlite": sqlite_value, "chroma": chroma_value, "faq": str(faq_value)}

    checks["faq_file"] = faq_value.is_file()
    faq_rows: list[dict[str, Any]] = []
    if checks["faq_file"]:
        try:
            faq_rows = json.loads(faq_value.read_text(encoding="utf-8"))
            checks["faq_hash"] = _sha256(faq_value) == spec["faq"]["sha256"]
            checks["faq_count"] = len(faq_rows) == spec["faq"]["count"]
        except (json.JSONDecodeError, OSError):
            checks["faq_hash"] = checks["faq_count"] = False
    else:
        checks["faq_hash"] = checks["faq_count"] = False

    evaluation = spec.get("evaluation") or {}
    evaluation_path = ROOT / str(evaluation.get("path") or "")
    checks["evaluation_file"] = evaluation_path.is_file()
    evaluation_cases: list[dict[str, Any]] = []
    if checks["evaluation_file"]:
        try:
            evaluation_text = evaluation_path.read_text(encoding="utf-8")
            evaluation_cases = [
                json.loads(line)
                for line in evaluation_text.splitlines()
                if line.strip()
            ]
            checks["evaluation_hash"] = _sha256(evaluation_path) == evaluation.get("sha256")
            checks["evaluation_count"] = len(evaluation_cases) == evaluation.get("case_count")
            checks["evaluation_reviewed"] = all(
                case.get("review_status") == "user_approved_for_demo"
                for case in evaluation_cases
            )
        except (json.JSONDecodeError, OSError):
            checks["evaluation_hash"] = False
            checks["evaluation_count"] = False
            checks["evaluation_reviewed"] = False
    else:
        checks["evaluation_hash"] = False
        checks["evaluation_count"] = False
        checks["evaluation_reviewed"] = False

    checks["sqlite"] = Path(sqlite_value).is_file()
    checks["chroma"] = Path(chroma_value).is_dir()
    if not checks["sqlite"]:
        return {"status": "not_ready", "checks": checks, "details": details}

    default_sqlite = sqlite_value == resolve_runtime_path(settings.sqlite_path)
    engine = None
    session_factory = async_session
    if not default_sqlite:
        engine, session_factory = build_runtime(sqlite_value)
    try:
        async with session_factory() as db:
            rows = list((await db.execute(
                select(Chunk)
                .join(Document, Document.id == Chunk.document_id)
                .where(Chunk.status == "ready", Document.status == "ready")
            )).scalars().all())
            active = get_active_index(sqlite_value)
            active_manifest = await db.scalar(
                select(IndexManifest).where(IndexManifest.id == active.get("manifest_id"))
            )
            documents = list((await db.execute(
                select(Document)
                .where(Document.status == "ready")
                .order_by(Document.content_sha256)
            )).scalars().all())
            faq_mirror = list((await db.execute(
                select(FAQ).where(FAQ.status == "active")
            )).scalars().all())

        expected_docs = {(item["content_sha256"], item["chunk_count"]) for item in spec["documents"]}
        actual_docs = {(item.content_sha256, int(item.chunk_count or 0)) for item in documents}
        checks["documents"] = actual_docs == expected_docs
        checks["canonical_count"] = len(rows) == spec["active_index"]["canonical_count"]

        fts = SQLiteLexicalRetriever(sqlite_value, namespace=active["fts_namespace"])
        fts_count = 0
        if fts.available:
            with sqlite3.connect(sqlite_value) as connection:
                fts_count = int(connection.execute(
                    f"SELECT COUNT(*) FROM {active['fts_namespace']}"
                ).fetchone()[0])
        vector_ids = None
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            client = chromadb.PersistentClient(
                path=chroma_value,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            collection = client.get_collection(active["vector_collection"])
            vector_ids = [str(item) for item in collection.get(include=[]).get("ids") or []]
        except Exception:
            vector_ids = None
        report = assess_active_index(
            active_manifest,
            active,
            rows,
            fts_available=fts.available,
            fts_count=fts_count,
            vector_ids=vector_ids,
            expected_embedding_model=settings.embedding_model,
            expected_config_hash=CHUNKING_CONFIG_HASH,
        )
        checks.update({f"index_{key}": value for key, value in report["checks"].items()})
        expected_active = spec["active_index"]
        checks["manifest_id"] = active.get("manifest_id") == expected_active["manifest_id"]
        checks["index_version"] = active["version"] == expected_active["version"]
        checks["fingerprint"] = report["details"]["canonical_fingerprint"] == expected_active["fingerprint"]
        checks["embedding_model"] = getattr(active_manifest, "embedding_model", "") == expected_active["embedding_model"]
        checks["config_hash"] = getattr(active_manifest, "config_hash", "") == expected_active["config_hash"]

        expected_faq_rows = {item["normalized_question"]: item["content_sha256"] for item in build_rows(faq_rows)}
        actual_faq_rows = {item.normalized_question: item.content_sha256 for item in faq_mirror}
        checks["faq_mirror"] = actual_faq_rows == expected_faq_rows
        details.update({
            "active": active,
            "canonical_count": len(rows),
            "fts_count": fts_count,
            "vector_count": len(vector_ids or []),
            "faq_json_count": len(expected_faq_rows),
            "faq_sqlite_count": len(actual_faq_rows),
            "index": report["details"],
        })
    finally:
        if engine is not None:
            await engine.dispose()

    return {"status": "ready" if all(checks.values()) else "not_ready", "checks": checks, "details": details}


def main() -> int:
    parser = argparse.ArgumentParser(description="只读校验冻结演示快照")
    parser.add_argument("--manifest", default=str(ROOT / "evals" / "demo_manifest.json"))
    parser.add_argument("--sqlite")
    parser.add_argument("--chroma")
    parser.add_argument("--faq-source")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = asyncio.run(verify_snapshot(
        args.manifest,
        sqlite_path=args.sqlite,
        chroma_path=args.chroma,
        faq_path=args.faq_source,
    ))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
