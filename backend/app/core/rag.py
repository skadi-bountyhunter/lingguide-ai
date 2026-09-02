"""混合 RAG 检索：SQLite FTS5/BM25 + Chroma/BGE + RRF。"""
from __future__ import annotations

import hashlib
import os
import warnings
from dataclasses import dataclass
from typing import Any, List

from loguru import logger

from app.config import resolve_runtime_path, settings as _cfg
from app.core.retrieval_types import RAGResult
from app.core.index_runtime import get_active_index
from app.core.timing import elapsed_ms, started

_CHROMA_STORE_PATH = resolve_runtime_path(_cfg.chroma_path)
_SQLITE_PATH = resolve_runtime_path(_cfg.sqlite_path)

# 必须在 sentence-transformers 导入前设置镜像地址。
if _cfg.hf_endpoint:
    os.environ["HF_ENDPOINT"] = _cfg.hf_endpoint
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
warnings.filterwarnings("ignore", message=".*NumPy 1.x.*")

RAG_AVAILABLE = False
if not _cfg.is_lite:
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from sentence_transformers import SentenceTransformer

        RAG_AVAILABLE = True
    except ImportError:
        logger.warning("ChromaDB / sentence-transformers 未安装，使用关键词检索降级")
else:
    logger.info("RAG lite 模式：仅启用 SQLite FTS5，不导入向量依赖")


@dataclass
class HybridSearchResult:
    """混合召回结果及诊断信息。"""

    results: list[RAGResult]
    route: str
    degraded: bool = False
    fallback_reason: str | None = None
    vector_count: int = 0
    keyword_count: int = 0
    index_version: str = "hybrid-v1"
    manifest_id: str | None = None
    channels: dict[str, dict[str, Any]] | None = None


class SimpleKeywordRetriever:
    """无 SQLite/FTS5 时的进程内兼容降级。"""

    def __init__(self):
        self._chunks: List[dict[str, Any]] = []

    def add_chunks(self, chunks: List[str], doc_id: str, metadatas=None):
        metadatas = metadatas or [{} for _ in chunks]
        for i, chunk in enumerate(chunks):
            meta = _normalized_chunk_metadata(chunk, doc_id, i, metadatas[i])
            chunk_id = meta["chunk_id"]
            self._chunks = [item for item in self._chunks if item["id"] != chunk_id]
            self._chunks.append({
                "id": chunk_id,
                "content": chunk,
                "document_id": meta["document_id"],
                "source": meta["source"],
                "metadata": meta,
            })

    def delete_document(self, doc_id: str):
        self._chunks = [c for c in self._chunks if c["document_id"] != str(doc_id)]

    def search(self, query: str, top_k: int = 5, score_threshold: float = 0.3) -> List[RAGResult]:
        query_words = set(query or "")
        scored = []
        for chunk in self._chunks:
            overlap = len(query_words & set(chunk["content"]))
            if overlap:
                scored.append((chunk, overlap / max(len(query_words), 1)))
        scored.sort(key=lambda item: (-item[1], item[0]["id"]))
        return [
            RAGResult(
                content=chunk["content"],
                source=chunk["source"],
                score=round(score, 4),
                chunk_id=chunk["id"],
                document_id=chunk["document_id"],
                retrieval_method="keyword",
                keyword_rank=index,
                keyword_score=round(score, 4),
                section=str(chunk.get("metadata", {}).get("section", "")),
                char_range=_char_range_from_metadata(chunk.get("metadata", {})),
                content_hash=str(chunk.get("metadata", {}).get("content_hash", "")),
                index_version=str(chunk.get("metadata", {}).get("index_version", "legacy-v1")),
                metadata=chunk.get("metadata", {}),
            )
            for index, (chunk, score) in enumerate(scored[:top_k], 1)
            if score >= score_threshold
        ]

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)


def _stable_chunk_id(doc_id: str, content: str, index: int) -> str:
    """生成不依赖文件名编码和进程状态的 chunk ID。"""
    digest = hashlib.sha256(f"{doc_id}\0{index}\0{content}".encode("utf-8")).hexdigest()[:24]
    return f"chunk_{digest}"


def _normalized_chunk_metadata(
    chunk: str,
    doc_id: str,
    index: int,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    """统一四种索引使用的 chunk 元数据，避免证据字段各自漂移。"""
    meta = dict(metadata or {})
    meta["chunk_id"] = str(meta.get("chunk_id") or _stable_chunk_id(doc_id, chunk, index))
    meta["document_id"] = str(meta.get("document_id") or doc_id)
    meta["source"] = str(meta.get("source") or doc_id)
    meta["content_hash"] = str(
        meta.get("content_hash") or hashlib.sha256(chunk.encode("utf-8")).hexdigest()
    )
    meta["index_version"] = str(meta.get("index_version") or "hybrid-v1")

    char_range = meta.get("char_range")
    if char_range and (meta.get("char_start") is None or meta.get("char_end") is None):
        try:
            meta["char_start"], meta["char_end"] = int(char_range[0]), int(char_range[1])
        except (TypeError, ValueError, IndexError):
            meta.pop("char_start", None)
            meta.pop("char_end", None)
    meta.pop("char_range", None)
    return meta


def _char_range_from_metadata(meta: dict[str, Any]) -> tuple[int, int] | None:
    """从新旧索引 metadata 读取合法字符范围。"""
    try:
        if meta.get("char_start") is not None and meta.get("char_end") is not None:
            return int(meta["char_start"]), int(meta["char_end"])
        legacy = meta.get("char_range")
        if legacy is not None:
            return int(legacy[0]), int(legacy[1])
    except (TypeError, ValueError, IndexError):
        return None
    return None


def _chroma_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """只向 Chroma 写入标量 metadata，避免列表值导致 upsert 失败。"""
    allowed = {
        "chunk_id", "document_id", "source", "content_hash", "index_version",
        "char_start", "char_end", "section", "page", "source_type",
    }
    output = {}
    for key in allowed:
        value = meta.get(key)
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            output[key] = value
        else:
            output[key] = str(value)
    return output


class VectorRAGService:
    """Chroma/BGE 向量检索适配器。"""

    def __init__(
        self,
        chroma_path: str | None = None,
        embedder=None,
        sqlite_path: str | None = None,
        collection_name: str | None = None,
    ):
        self.chroma_path = resolve_runtime_path(chroma_path or _CHROMA_STORE_PATH)
        self.sqlite_path = os.path.abspath(sqlite_path or _SQLITE_PATH)
        self._target_collection_name = collection_name
        self._active_collection_name = None
        self._client = None
        self._collection = None
        self._embedder = embedder
        self.last_missing_count = 0

    @property
    def client(self):
        if self._client is None:
            os.makedirs(self.chroma_path, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=self.chroma_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    @property
    def embedder(self):
        if self._embedder is None:
            try:
                self._embedder = SentenceTransformer(
                    _cfg.embedding_model,
                    local_files_only=not _cfg.embedding_allow_download,
                )
            except Exception as exc:
                mode = "本地缓存" if not _cfg.embedding_allow_download else "配置的模型源"
                raise RuntimeError(f"embedding 模型无法从{mode}加载") from exc
        return self._embedder

    @property
    def collection(self):
        if self._target_collection_name:
            collection_name = self._target_collection_name
            version = "shadow"
            factory = lambda: self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine", "index_version": version},
            )
        else:
            active = get_active_index(self.sqlite_path)
            collection_name = active["vector_collection"]
            # 未初始化的隔离/历史库允许走 legacy collection，正式 active manifest
            # 一旦存在则必须严格读取，防止缺失 collection 被静默创建为“空索引”。
            if active.get("manifest_id"):
                factory = lambda: self.client.get_collection(name=collection_name)
            else:
                factory = lambda: self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine", "index_version": active["version"]},
                )
        if self._collection is None or self._active_collection_name != collection_name:
            self._collection = factory()
            self._active_collection_name = collection_name
        return self._collection

    def embed(self, texts: List[str]) -> List[List[float]]:
        return self.embedder.encode(texts, normalize_embeddings=True).tolist()

    def add_chunks(self, chunks: List[str], doc_id: str, metadatas=None):
        if not chunks:
            return
        metadatas = metadatas or [{} for _ in chunks]
        ids = []
        clean_metadata = []
        for index, (chunk, metadata) in enumerate(zip(chunks, metadatas)):
            meta = _normalized_chunk_metadata(chunk, doc_id, index, metadata)
            ids.append(meta["chunk_id"])
            clean_metadata.append(_chroma_metadata(meta))
        self.collection.upsert(
            ids=ids,
            embeddings=self.embed(chunks),
            documents=chunks,
            metadatas=clean_metadata,
        )

    def delete_document(self, doc_id: str):
        """按稳定 document_id 删除，避免同名文件互相影响。"""
        results = self.collection.get(where={"document_id": str(doc_id)})
        if results.get("ids"):
            self.collection.delete(ids=results["ids"])

    def search(self, query: str, top_k: int = 30, score_threshold: float = 0.0) -> List[RAGResult]:
        # 多取候选再做 canonical 回查，避免历史 orphan 向量挤占有效结果名额。
        query_embedding = self.embed([query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(max(top_k * 3, top_k), 100),
            include=["documents", "metadatas", "distances"],
        )
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]
        output = []
        for rank, (doc, meta, distance) in enumerate(zip(documents, metadatas, distances), 1):
            meta = dict(meta or {})
            score = round(1 - float(distance), 4)
            if score < score_threshold:
                continue
            chunk_id = str(meta.get("chunk_id", meta.get("id", "")))
            if not chunk_id:
                continue
            output.append(RAGResult(
                content=doc,
                source=str(meta.get("source", "unknown")),
                score=score,
                chunk_id=chunk_id,
                document_id=str(meta.get("document_id", "")),
                rank=rank,
                retrieval_method="vector",
                vector_rank=rank,
                vector_score=score,
                section=str(meta.get("section", "")),
                page=meta.get("page"),
                char_range=_char_range_from_metadata(meta),
                content_hash=str(meta.get("content_hash", "")),
                index_version=str(meta.get("index_version", "legacy-v1")),
                metadata=meta,
            ))
        canonical = SQLiteLexicalRetriever(self.sqlite_path)
        output, self.last_missing_count = canonical.hydrate_results(output)
        return output[:top_k]

    @property
    def chunk_count(self) -> int:
        return self.collection.count()


class SQLiteLexicalRetriever:
    """基于 SQLite FTS5 的持久化关键词召回。"""

    def __init__(
        self,
        db_path: str = _SQLITE_PATH,
        ensure_schema: bool = False,
        namespace: str | None = None,
    ):
        self.db_path = os.path.abspath(db_path)
        self._target_namespace = namespace
        self._active_namespace = None
        self.available = False
        if ensure_schema:
            self._ensure_schema()
        else:
            self._check_schema()

    def _check_schema(self):
        import sqlite3

        if not os.path.exists(self.db_path):
            self.available = False
            return
        try:
            namespace = self._namespace()
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                    (namespace,),
                ).fetchone()
                self.available = row is not None
                self._active_namespace = namespace
        except sqlite3.Error as exc:
            self.available = False
            logger.warning(f"SQLite FTS5 不可用: {exc}")

    def _ensure_schema(self):
        """仅供显式初始化流程使用，不在检索器构造时创建 schema。"""
        import sqlite3

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            namespace = self._namespace()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    f"CREATE VIRTUAL TABLE IF NOT EXISTS {namespace} "
                    "USING fts5(chunk_id UNINDEXED, document_id UNINDEXED, source UNINDEXED, search_text)"
                )
                self.available = True
        except sqlite3.Error as exc:
            logger.warning(f"SQLite FTS5 不可用: {exc}")

    def _namespace(self) -> str:
        """读取目标或当前 active 的 FTS namespace。"""
        if self._target_namespace:
            return self._target_namespace
        return get_active_index(self.db_path)["fts_namespace"]

    def _refresh_schema(self):
        """active manifest 切换后刷新 FTS 可用状态。"""
        namespace = self._namespace()
        if namespace != self._active_namespace:
            self._check_schema()

    @staticmethod
    def _tokens(text: str) -> list[str]:
        import re
        import unicodedata

        normalized = unicodedata.normalize("NFKC", str(text or "")).casefold()
        normalized = re.sub(r"\s+", "", normalized)
        try:
            import jieba
            words = [word.strip() for word in jieba.lcut_for_search(normalized) if word.strip()]
        except ImportError:
            words = []
        # 中文 FTS 默认 tokenizer 对连续汉字支持有限，补充二元组和数字词。
        compact = re.sub(r"[^\w一-鿿]", "", normalized)
        words.extend(compact[index:index + 2] for index in range(max(0, len(compact) - 1)))
        return list(dict.fromkeys(words))

    def index_chunks(self, chunks: list[dict[str, Any]]):
        self._refresh_schema()
        if not self.available or not chunks:
            return
        import sqlite3

        namespace = self._namespace()
        with sqlite3.connect(self.db_path) as conn:
            for item in chunks:
                chunk_id = str(item["chunk_id"])
                conn.execute(f"DELETE FROM {namespace} WHERE chunk_id = ?", (chunk_id,))
                search_text = str(item.get("search_text") or item.get("content") or "")
                tokenized = " ".join(self._tokens(search_text))
                conn.execute(
                    f"INSERT INTO {namespace}(chunk_id, document_id, source, search_text) VALUES (?, ?, ?, ?)",
                    (chunk_id, str(item.get("document_id", "")), str(item.get("source", "")), tokenized),
                )

    def delete_document(self, doc_id: str):
        self._refresh_schema()
        if not self.available:
            return
        import sqlite3
        namespace = self._namespace()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"DELETE FROM {namespace} WHERE document_id = ?", (str(doc_id),))

    def _canonical_chunks(self, chunk_ids: list[str]) -> dict[str, dict[str, Any]]:
        """按稳定 chunk ID 读取可作为证据的 canonical Chunk。"""
        if not chunk_ids or not os.path.exists(self.db_path):
            return {}
        import sqlite3

        placeholders = ",".join("?" for _ in chunk_ids)
        try:
            with sqlite3.connect(self.db_path) as conn:
                try:
                    rows = conn.execute(
                        f"SELECT c.id, c.content, c.document_id, c.section_title, c.char_start, c.char_end, "
                        f"c.content_sha256, c.index_version, d.filename "
                        f"FROM chunks c LEFT JOIN documents d ON d.id = c.document_id "
                        f"WHERE c.id IN ({placeholders}) "
                        "AND COALESCE(c.status, 'ready') = 'ready' "
                        "AND COALESCE(d.status, 'ready') = 'ready'",
                        chunk_ids,
                    ).fetchall()
                except sqlite3.Error:
                    # 兼容只有 chunks 表的临时库或旧库，仍不接受 deleted chunk。
                    rows = conn.execute(
                        f"SELECT id, content, document_id, section_title, char_start, char_end, "
                        f"content_sha256, index_version, '' FROM chunks "
                        f"WHERE id IN ({placeholders}) AND COALESCE(status, 'ready') = 'ready'",
                        chunk_ids,
                    ).fetchall()
        except sqlite3.Error:
            return {}
        return {
            str(row[0]): {
                "content": row[1],
                "document_id": str(row[2] or ""),
                "section": str(row[3] or ""),
                "char_range": (row[4], row[5]) if row[4] is not None and row[5] is not None else None,
                "content_hash": str(row[6] or ""),
                "index_version": str(row[7] or "legacy-v1"),
                "source": str(row[8] or ""),
            }
            for row in rows
        }

    def hydrate_results(self, results: list[RAGResult]) -> tuple[list[RAGResult], int]:
        """用 canonical Chunk 覆盖向量候选，返回结果和无法回查数量。"""
        if not results:
            return [], 0
        canonical = self._canonical_chunks([item.chunk_id for item in results if item.chunk_id])
        hydrated = []
        missing = 0
        for item in results:
            chunk = canonical.get(item.chunk_id)
            if not chunk:
                missing += 1
                continue
            item.content = chunk["content"]
            item.document_id = chunk["document_id"]
            item.source = chunk["source"] or item.source
            item.section = chunk["section"]
            item.char_range = chunk["char_range"]
            item.content_hash = chunk["content_hash"]
            item.index_version = chunk["index_version"]
            item.metadata = {**item.metadata, **chunk}
            hydrated.append(item)
        return hydrated, missing

    def search(self, query: str, top_k: int = 30) -> list[RAGResult]:
        self._refresh_schema()
        if not self.available:
            return []
        import sqlite3

        tokens = self._tokens(query)
        if not tokens:
            return []
        match_query = " OR ".join(f'"{token.replace(chr(34), "")}"' for token in tokens[:32])
        namespace = self._namespace()
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT chunk_id, document_id, source, bm25({namespace}) "
                f"FROM {namespace} WHERE {namespace} MATCH ? ORDER BY bm25({namespace}), chunk_id LIMIT ?",
                (match_query, top_k),
            ).fetchall()

        canonical = self._canonical_chunks([str(row[0]) for row in rows])
        results = []
        for index, row in enumerate(rows, 1):
            chunk = canonical.get(str(row[0]))
            if not chunk:
                continue
            score = round(-float(row[3]), 4)
            results.append(RAGResult(
                content=chunk["content"],
                source=chunk["source"] or row[2] or "unknown",
                score=score,
                chunk_id=str(row[0]),
                document_id=chunk["document_id"] or str(row[1] or ""),
                rank=index,
                retrieval_method="keyword",
                keyword_rank=index,
                keyword_score=score,
                section=chunk["section"],
                char_range=chunk["char_range"],
                content_hash=chunk["content_hash"],
                index_version=chunk["index_version"],
                metadata=chunk,
            ))
        return results


class HybridRAGService:
    """组合向量和 FTS 召回，并以 RRF 输出统一结果。"""

    def __init__(
        self,
        sqlite_path: str | None = None,
        chroma_path: str | None = None,
        embedder=None,
        vector_collection: str | None = None,
        fts_namespace: str | None = None,
    ):
        resolved_sqlite = sqlite_path or _SQLITE_PATH
        self.vector = VectorRAGService(
            chroma_path=chroma_path,
            embedder=embedder,
            sqlite_path=resolved_sqlite,
            collection_name=vector_collection,
        ) if RAG_AVAILABLE else None
        self.keyword = SQLiteLexicalRetriever(
            db_path=resolved_sqlite,
            namespace=fts_namespace,
        )
        self._fallback = SimpleKeywordRetriever()
        self._legacy_indexed = False
        self._last_legacy_missing = 0

    @property
    def collection(self):
        return self.vector.collection if self.vector else None

    @property
    def keyword_namespace(self) -> str:
        return self.keyword._namespace()

    @property
    def client(self):
        return self.vector.client if self.vector else None

    @property
    def chunk_count(self):
        if self.vector:
            return self.vector.chunk_count
        return 0

    def _index_legacy_vectors(self):
        """首次使用 FTS 时把旧 Chroma 数据补入 FTS，避免升级后关键词路为空。"""
        if self._legacy_indexed or not self.vector or not self.keyword.available:
            return
        self._legacy_indexed = True
        try:
            data = self.vector.collection.get(include=["documents", "metadatas"])
            chunks = []
            for content, metadata in zip(data.get("documents") or [], data.get("metadatas") or []):
                meta = dict(metadata or {})
                chunk_id = str(meta.get("chunk_id", ""))
                if not chunk_id:
                    continue
                chunks.append({
                    "chunk_id": chunk_id,
                    "document_id": meta.get("document_id", ""),
                    "source": meta.get("source", ""),
                    "content": content,
                    "search_text": content,
                })
            self.keyword.index_chunks(chunks)
        except Exception as exc:
            logger.warning(f"旧向量补建 FTS 失败: {exc}")

    def add_chunks(self, chunks: List[str], doc_id: str, metadatas=None):
        normalized = [
            _normalized_chunk_metadata(chunk, doc_id, index, (metadatas or [{} for _ in chunks])[index])
            for index, chunk in enumerate(chunks)
        ]
        if self.vector:
            self.vector.add_chunks(chunks, doc_id, normalized)
        else:
            self._fallback.add_chunks(chunks, doc_id, normalized)
        self.keyword.index_chunks([
            {
                **metadata,
                "content": chunk,
                "search_text": metadata.get("search_text", chunk),
            }
            for chunk, metadata in zip(chunks, normalized)
        ])

    def delete_document(self, doc_id: str):
        if self.vector:
            self.vector.delete_document(doc_id)
        self._fallback.delete_document(doc_id)
        self.keyword.delete_document(doc_id)

    @staticmethod
    def _merge(vector_results, keyword_results, final_k: int, rrf_k: int = 60):
        merged: dict[str, RAGResult] = {}
        for method, results in (("vector", vector_results), ("keyword", keyword_results)):
            for rank, result in enumerate(results, 1):
                key = result.chunk_id or hashlib.sha256(result.content.encode("utf-8")).hexdigest()
                current = merged.get(key)
                if current is None:
                    current = RAGResult(
                        content=result.content,
                        source=result.source,
                        score=0.0,
                        chunk_id=key,
                        document_id=result.document_id,
                        source_type=result.source_type,
                        retrieval_method=method,
                        section=result.section,
                        page=result.page,
                        char_range=result.char_range,
                        content_hash=result.content_hash,
                        index_version=result.index_version,
                        metadata=dict(result.metadata),
                    )
                    merged[key] = current
                else:
                    # 后到的 canonical 结果可以补齐先到结果的缺失字段，但不能被空值覆盖。
                    for field in ("content", "source", "document_id", "section", "page", "char_range", "content_hash", "index_version"):
                        value = getattr(result, field)
                        if value not in (None, "", []):
                            if field == "content" or getattr(current, field) in (None, "", []):
                                setattr(current, field, value)
                    current.metadata = {**current.metadata, **{k: v for k, v in result.metadata.items() if v not in (None, "", [])}}
                current.fused_score = (current.fused_score or 0.0) + 1.0 / (rrf_k + rank)
                if method == "vector":
                    current.vector_rank = rank
                    current.vector_score = result.vector_score if result.vector_score is not None else result.score
                else:
                    current.keyword_rank = rank
                    current.keyword_score = result.keyword_score if result.keyword_score is not None else result.score
                if current.vector_rank and current.keyword_rank:
                    current.retrieval_method = "hybrid"
        ordered = sorted(
            merged.values(),
            key=lambda item: (-(item.fused_score or 0.0), min(item.vector_rank or 10**9, item.keyword_rank or 10**9), item.chunk_id),
        )
        for rank, result in enumerate(ordered[:final_k], 1):
            result.rank = rank
            result.score = round(result.fused_score or 0.0, 6)
        return ordered[:final_k]

    def search_with_trace(self, query: str, candidate_k: int = 30, final_k: int = 5) -> HybridSearchResult:
        active = get_active_index(self.vector.sqlite_path) if self.vector else get_active_index(self.keyword.db_path)
        vector_results = []
        keyword_results = []
        failures = []
        channels = {
            "bge": {"status": "skipped", "latency_ms": 0, "count": 0},
            "fts": {"status": "skipped", "latency_ms": 0, "count": 0, "fallback_used": False},
        }
        if self.vector:
            started_at = started()
            try:
                vector_results = self.vector.search(query, top_k=candidate_k)
                channels["bge"] = {
                    "status": "ok" if vector_results else "empty",
                    "latency_ms": elapsed_ms(started_at),
                    "count": len(vector_results),
                }
                if self.vector.last_missing_count:
                    failures.append(f"vector:canonical_missing={self.vector.last_missing_count}")
                    channels["bge"]["reason"] = "canonical_missing"
            except Exception as exc:
                reason = type(exc).__name__
                failures.append(f"vector:{reason}")
                channels["bge"] = {
                    "status": "failed",
                    "latency_ms": elapsed_ms(started_at),
                    "count": 0,
                    "reason": reason,
                }
        else:
            failures.append("vector:unavailable")
            channels["bge"] = {"status": "unavailable", "latency_ms": 0, "count": 0, "reason": "unavailable"}

        started_at = started()
        try:
            keyword_results = self.keyword.search(query, top_k=candidate_k)
            fallback_used = not keyword_results and not self.keyword.available
            if fallback_used:
                keyword_results = self._fallback.search(query, top_k=candidate_k)
            channels["fts"] = {
                "status": "ok" if keyword_results else ("unavailable" if fallback_used else "empty"),
                "latency_ms": elapsed_ms(started_at),
                "count": len(keyword_results),
                "fallback_used": fallback_used,
            }
        except Exception as exc:
            reason = type(exc).__name__
            failures.append(f"keyword:{reason}")
            keyword_results = self._fallback.search(query, top_k=candidate_k)
            channels["fts"] = {
                "status": "failed",
                "latency_ms": elapsed_ms(started_at),
                "count": len(keyword_results),
                "fallback_used": True,
                "reason": reason,
            }

        results = self._merge(vector_results, keyword_results, final_k)
        if vector_results and keyword_results:
            route = "hybrid"
        elif vector_results:
            route = "vector"
        elif keyword_results:
            route = "keyword"
        else:
            route = "no_match"
        index_version = str(active["version"])
        return HybridSearchResult(
            results=results,
            route=route,
            degraded=bool(failures),
            fallback_reason=";".join(failures) or None,
            vector_count=len(vector_results),
            keyword_count=len(keyword_results),
            index_version=index_version,
            manifest_id=active.get("manifest_id"),
            channels=channels,
        )

    def search(self, query: str, top_k: int = 5, score_threshold: float = 0.0) -> list[RAGResult]:
        result = self.search_with_trace(query, final_k=top_k)
        return [item for item in result.results if item.score >= score_threshold]


if RAG_AVAILABLE:
    logger.info("使用混合 RAG 模式（Chroma + SQLite FTS5）")
else:
    logger.warning("向量依赖不可用，使用 SQLite FTS5 关键词模式")
rag_service = HybridRAGService()
