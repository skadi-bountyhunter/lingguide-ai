"""知识库初始化脚本 — 按文档幂等导入 SQLite、FTS5 和 Chroma。"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import async_session, init_db
from app.services.knowledge_service import KnowledgeService
from app.config import settings
from loguru import logger

DOC_DIR = os.path.join(os.path.dirname(__file__), "..", "示范景区公开资料包")


async def import_all():
    """逐文档导入，不清空现有 collection。"""
    if not os.path.exists(DOC_DIR):
        logger.error(f"资料目录不存在: {DOC_DIR}")
        return
    await init_db()
    service = KnowledgeService(settings.upload_dir)
    async with async_session() as db:
        for filename in sorted(os.listdir(DOC_DIR)):
            if not filename.lower().endswith((".docx", ".txt", ".md")):
                continue
            try:
                content = open(os.path.join(DOC_DIR, filename), "rb").read()
                document = await service.ingest(db, filename, content)
                logger.info(f"完成: {filename} ({document.chunk_count} 个分块)")
            except Exception as exc:
                logger.error(f"导入失败 {filename}: {exc}")


if __name__ == "__main__":
    asyncio.run(import_all())
