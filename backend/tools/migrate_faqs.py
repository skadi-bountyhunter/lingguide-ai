"""将 faqs.json 导入 SQLite 的可审计迁移工具。

默认只生成对照报告，不写数据库；执行写入必须显式传入 --apply。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.api.knowledge import FAQ_FILE, _load_faqs  # noqa: E402
from app.core.database import async_session, init_db  # noqa: E402
from app.models import FAQ  # noqa: E402
from app.tools_faq import build_rows, rows_to_payload  # noqa: E402

_build_rows = build_rows


async def main(apply: bool) -> int:
    source = Path(FAQ_FILE)
    faqs = _load_faqs()
    rows = _build_rows(faqs)
    print(json.dumps({"source": str(source), "count": len(rows), "apply": apply}, ensure_ascii=False, indent=2))
    if not apply:
        print("dry-run：未修改数据库。需要写入时显式传入 --apply。")
        return 0

    await init_db()
    async with async_session() as db:
        existing = {row.normalized_question: row for row in (await db.execute(select(FAQ))).scalars().all()}
        inserted = 0
        updated = 0
        for item in rows:
            row = existing.get(item["normalized_question"])
            payload = rows_to_payload(item)
            if row is None:
                db.add(FAQ(**payload))
                inserted += 1
            elif row.content_sha256 != item["content_sha256"]:
                for key, value in payload.items():
                    setattr(row, key, value)
                updated += 1
        await db.commit()
    print(json.dumps({"inserted": inserted, "updated": updated}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="确认后写入 SQLite")
    args = parser.parse_args()
    import asyncio
    raise SystemExit(asyncio.run(main(args.apply)))
