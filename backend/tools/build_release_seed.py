"""从空库和公开种子函数生成便携版发布 seed。"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# 每次使用系统临时目录创建全新空库，绝不读取或删除项目当前数据库。
_BUILD_ROOT = Path(tempfile.mkdtemp(prefix="lingguide-release-seed-"))
os.environ.setdefault("RUNTIME_MODE", "development")
os.environ["RAG_MODE"] = "lite"
os.environ["SQLITE_PATH"] = str(_BUILD_ROOT / "lingguide.db")
os.environ["UPLOAD_DIR"] = str(_BUILD_ROOT / "uploads")
os.environ["CHROMA_PATH"] = str(_BUILD_ROOT / "chroma")
os.environ["FAQ_PATH"] = str(_BUILD_ROOT / "faqs.json")


async def build_release_seed(output_dir: Path) -> dict[str, object]:
    """创建纯净 SQLite、公开 FAQ 和完整性清单。"""
    from sqlalchemy import select

    from app.api.knowledge import _load_faqs
    from app.api.routes import seed_routes
    from app.api.spots import seed_spots
    from app.core.database import async_session, engine, init_db
    from app.core.rag import SQLiteLexicalRetriever
    from app.models import Chunk, Document, FAQ
    from app.tools_faq import build_rows, rows_to_payload

    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    database_path = _BUILD_ROOT / "lingguide.db"

    await init_db()
    async with async_session() as db:
        await seed_spots(db)
        await seed_routes(db)
        existing = {
            row.normalized_question: row
            for row in (await db.execute(select(FAQ))).scalars().all()
        }
        faq_rows = build_rows(_load_faqs())
        for item in faq_rows:
            payload = rows_to_payload(item)
            row = existing.get(item["normalized_question"])
            if row is None:
                db.add(FAQ(**payload))
            else:
                for key, value in payload.items():
                    setattr(row, key, value)

        # 把公开 FAQ 同步为 canonical 文档与 FTS 分块，Lite 模式也能离线检索。
        document = Document(
            id="release_faq_document",
            filename="灵境导游公开FAQ",
            file_type="builtin",
            file_size=0,
            status="ready",
            chunk_count=len(faq_rows),
            storage_key="builtin:faqs",
            content_sha256=hashlib.sha256(
                json.dumps(faq_rows, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            index_version="lite-v1",
            updated_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(document)
        chunks = []
        for index, item in enumerate(faq_rows):
            content = f"问题：{item['question']}\n回答：{item['answer']}"
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            chunks.append(Chunk(
                id=f"release_faq_{index + 1:03d}",
                document_id=document.id,
                content=content,
                chunk_index=index,
                normalized_content=content,
                search_text=" ".join(filter(None, [
                    item["question"], item["answer"], item.get("match_text", ""),
                ])),
                content_sha256=content_hash,
                vector_id="",
                index_version="lite-v1",
                status="ready",
                section_title=item["question"],
                char_start=0,
                char_end=len(content),
            ))
        db.add_all(chunks)
        await db.commit()

    lexical = SQLiteLexicalRetriever(str(database_path), ensure_schema=True)
    lexical.index_chunks([
        {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "source": "灵境导游公开FAQ",
            "content": chunk.content,
            "search_text": chunk.search_text,
        }
        for chunk in chunks
    ])
    await engine.dispose()

    target_db = output_dir / "lingguide.db"
    temporary = output_dir / "lingguide.db.tmp"
    shutil.copy2(database_path, temporary)
    os.replace(temporary, target_db)

    faq_source = BACKEND_ROOT / "app" / "faqs.json"
    target_faq = output_dir / "faqs.json"
    shutil.copy2(faq_source, target_faq)

    with sqlite3.connect(target_db) as connection:
        counts = {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("spots", "routes", "faqs", "documents", "chunks", "chunk_fts")
        }
    manifest = {
        "version": 1,
        "rag_mode": "lite",
        "database": "lingguide.db",
        "faq": "faqs.json",
        "counts": counts,
        "sha256": {
            "lingguide.db": hashlib.sha256(target_db.read_bytes()).hexdigest(),
            "faqs.json": hashlib.sha256(target_faq.read_bytes()).hexdigest(),
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    shutil.rmtree(_BUILD_ROOT, ignore_errors=True)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成 Windows 便携版公开 seed")
    parser.add_argument("--output-dir", required=True, help="绝对输出目录")
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        parser.error("--output-dir 必须是绝对路径")
    manifest = asyncio.run(build_release_seed(output_dir))
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
