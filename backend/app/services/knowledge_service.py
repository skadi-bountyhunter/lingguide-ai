"""知识文档摄取：安全存储、稳定分块、SQLite/FTS5/Chroma 同步。"""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
import uuid
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import resolve_runtime_path, settings
from app.core.index_runtime import get_active_index
from app.core.rag import rag_service
from app.models import Chunk, Document, IndexManifest
from app.services.index_lifecycle import IndexLifecycleService

INDEX_VERSION = "hybrid-v1"
_INGEST_LOCK = asyncio.Lock()


class IndexNotReadyError(RuntimeError):
    """生产严格模式下没有可用 active manifest。"""
ALLOWED_EXTENSIONS = {"txt", "md", "docx"}
MAX_FILE_SIZE = 20 * 1024 * 1024


class KnowledgeService:
    """同步完成 MVP 索引，失败时保留文档错误状态。"""

    def __init__(self, upload_dir: str, rag=None, index_lifecycle=None, allow_unmanaged_index=None):
        self.upload_dir = Path(upload_dir).resolve()
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        # 默认复用线上 RAG；测试或显式初始化流程可注入隔离实例。
        self._rag = rag or rag_service
        self._allow_unmanaged_index = (
            bool(allow_unmanaged_index)
            if allow_unmanaged_index is not None
            else bool(index_lifecycle is None and rag is not None)
        )
        if index_lifecycle is not None:
            self._index_lifecycle = index_lifecycle
        else:
            sqlite_path = getattr(getattr(self._rag, "keyword", None), "db_path", None)
            chroma_path = getattr(getattr(self._rag, "vector", None), "chroma_path", None)
            self._index_lifecycle = IndexLifecycleService(sqlite_path, chroma_path)

    async def _require_active_manifest(self, db: AsyncSession) -> IndexManifest | None:
        """增量写入仅允许落在已激活且可追踪的 manifest 上。"""
        if self._allow_unmanaged_index:
            return None
        active = get_active_index(self._index_lifecycle.sqlite_path)
        manifest_id = active.get("manifest_id")
        if not manifest_id:
            raise IndexNotReadyError(
                "active 索引未就绪，请先完成 shadow build、validate 和 activate"
            )
        manifest = await db.scalar(
            select(IndexManifest).where(
                IndexManifest.id == manifest_id,
                IndexManifest.state == "active",
            )
        )
        if not manifest:
            raise IndexNotReadyError(
                "active manifest 未就绪，请先完成 shadow build、validate 和 activate"
            )
        return manifest

    @staticmethod
    def _safe_filename(filename: str) -> str:
        raw = str(filename or "")
        name = Path(raw).name
        if not name or name in {".", ".."} or "/" in raw or "\\" in raw or name != raw:
            raise ValueError("文件名不合法")
        return name

    async def ingest(self, db: AsyncSession, filename: str, content: bytes) -> Document:
        async with _INGEST_LOCK:
            return await self._ingest_locked(db, filename, content)

    async def _ingest_locked(self, db: AsyncSession, filename: str, content: bytes) -> Document:
        safe_name = self._safe_filename(filename)
        if len(content) > MAX_FILE_SIZE:
            raise ValueError("文件大小超过 20MB 限制")
        ext = Path(safe_name).suffix.lower().lstrip(".")
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError("当前仅支持 txt、md、docx 文件")

        content_hash = hashlib.sha256(content).hexdigest()
        existing = await db.scalar(select(Document).where(Document.content_sha256 == content_hash))
        if existing and existing.status == "ready":
            return existing

        await self._require_active_manifest(db)
        document = existing or Document(id=uuid.uuid4().hex, filename=safe_name)
        document.filename = safe_name
        document.file_type = ext
        document.file_size = len(content)
        document.content_sha256 = content_hash
        document.storage_key = f"{document.id}.{ext}"
        active_index = get_active_index(self._index_lifecycle.sqlite_path)
        index_version = active_index["version"]
        document.index_version = index_version
        document.status = "processing"
        document.error_message = ""
        db.add(document)
        await db.flush()

        target = self.upload_dir / document.storage_key
        target.write_bytes(content)
        try:
            text = self._parse_bytes(content, ext, target)
            chunks = self._split_text_with_offsets(text)
            await db.execute(delete(Chunk).where(Chunk.document_id == document.id))
            chunk_rows = []
            for index, (chunk_text, char_start, char_end) in enumerate(chunks):
                chunk_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
                chunk_id = hashlib.sha256(
                    f"{document.id}\0{content_hash}\0{index_version}\0{index}\0{chunk_hash}".encode("utf-8")
                ).hexdigest()
                chunk_rows.append(Chunk(
                    id=chunk_id,
                    document_id=document.id,
                    content=chunk_text,
                    chunk_index=index,
                    normalized_content=chunk_text,
                    search_text=chunk_text,
                    content_sha256=chunk_hash,
                    vector_id=chunk_id,
                    index_version=index_version,
                    status="ready",
                    char_start=char_start,
                    char_end=char_end,
                ))
            db.add_all(chunk_rows)
            await db.flush()
            # 先提交 SQLAlchemy 事务，再由同步索引器写 FTS；否则两个 SQLite
            # 连接会同时持有写锁，导入时会触发 database is locked。
            await db.commit()
            self._rag.add_chunks(
                [row.content for row in chunk_rows],
                document.id,
                [
                    {
                        "chunk_id": row.id,
                        "document_id": document.id,
                        "source": safe_name,
                        "search_text": row.search_text,
                        "content_hash": row.content_sha256,
                        "char_start": row.char_start,
                        "char_end": row.char_end,
                        "index_version": index_version,
                    }
                    for row in chunk_rows
                ],
            )
            document.chunk_count = len(chunk_rows)
            document.status = "ready"
            await db.commit()
            if not self._allow_unmanaged_index:
                await self._index_lifecycle.refresh_active_manifest(db)
            return document
        except Exception as exc:
            try:
                self._rag.delete_document(document.id)
            except Exception:
                pass
            document.status = "failed"
            document.error_message = str(exc)[:500]
            await db.commit()
            raise

    async def delete(self, db: AsyncSession, document_id: str):
        async with _INGEST_LOCK:
            return await self._delete_locked(db, document_id)

    async def _delete_locked(self, db: AsyncSession, document_id: str):
        document = await db.get(Document, document_id)
        if not document:
            return False
        await self._require_active_manifest(db)
        self._rag.delete_document(document.id)
        await db.delete(document)
        await db.commit()
        if not self._allow_unmanaged_index:
            await self._index_lifecycle.refresh_active_manifest(db)
        target = self.upload_dir / document.storage_key
        if target.exists():
            target.unlink()
        return True

    @staticmethod
    def _parse_bytes(content: bytes, ext: str, target: Path) -> str:
        if ext in {"txt", "md"}:
            return content.decode("utf-8")
        if ext == "docx":
            from app.api.knowledge import _parse_document
            return _parse_document(str(target), ext)
        raise ValueError("不支持的文档格式")

    @staticmethod
    def _normalized_text(text: str) -> str:
        return re.sub(r"\n{3,}", "\n\n", text or "").strip()

    @classmethod
    def _split_text_with_offsets(
        cls,
        text: str,
        chunk_size: int = 600,
        overlap: int = 80,
    ) -> list[tuple[str, int, int]]:
        """按规范化全文切分，并返回可回查的绝对字符范围。"""
        normalized = cls._normalized_text(text)
        chunks = []
        start = 0
        step = max(chunk_size - overlap, 1)
        while start < len(normalized):
            end = min(start + chunk_size, len(normalized))
            left = start + len(normalized[start:end]) - len(normalized[start:end].lstrip())
            right = end - len(normalized[start:end]) + len(normalized[start:end].rstrip())
            if left < right:
                chunks.append((normalized[left:right], left, right))
            start += step
        return chunks

    @classmethod
    def _split_text(cls, text: str, chunk_size: int = 600, overlap: int = 80) -> list[str]:
        """保留旧调用方返回纯文本分块的兼容接口。"""
        return [chunk for chunk, _, _ in cls._split_text_with_offsets(text, chunk_size, overlap)]
