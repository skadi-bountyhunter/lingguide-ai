"""数据库连接管理 — SQLite（零配置）"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import resolve_runtime_path, settings
from sqlalchemy.orm import DeclarativeBase
from loguru import logger


class Base(DeclarativeBase):
    pass


_sqlite_path = resolve_runtime_path(settings.sqlite_path)


def _build_engine(sqlite_path: str):
    sqlite_url = f"sqlite+aiosqlite:///{sqlite_path}"
    return create_async_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})


engine = _build_engine(_sqlite_path)
logger.info(f"数据库: SQLite ({_sqlite_path})")


def _ensure_sqlite_schema_sync():
    """在测试客户端未触发生命周期时，也保证旧 SQLite 具备新增列。"""
    import sqlite3

    columns = {
        "interactions": {
            "user_id": "TEXT",
            "citations_json": "TEXT DEFAULT '[]'",
            "retrieval_json": "TEXT DEFAULT '{}'",
            "trace_id": "TEXT DEFAULT ''",
            "spot_id": "TEXT",
        },
        "documents": {
            "storage_key": "TEXT",
            "content_sha256": "TEXT",
            "index_version": "TEXT DEFAULT 'hybrid-v1'",
            "error_message": "TEXT",
        },
        "users": {
            "role": "TEXT DEFAULT 'visitor'",
        },
        "saved_routes": {
            "citations": "TEXT DEFAULT '[]'",
            "retrieval": "TEXT DEFAULT '{}'",
            "trace_id": "TEXT DEFAULT ''",
            "index_version": "TEXT DEFAULT ''",
        },
        "faqs": {
            "entities": "TEXT DEFAULT '[]'",
            "intent": "TEXT DEFAULT 'general_intro'",
            "intent_keywords": "TEXT DEFAULT '[]'",
            "exact_questions": "TEXT DEFAULT '[]'",
            "normalized_question": "TEXT DEFAULT ''",
            "content_sha256": "TEXT DEFAULT ''",
            "status": "TEXT DEFAULT 'active'",
        },
        "chunks": {
            "normalized_content": "TEXT",
            "search_text": "TEXT",
            "content_sha256": "TEXT",
            "vector_id": "TEXT",
            "index_version": "TEXT DEFAULT 'hybrid-v1'",
            "status": "TEXT DEFAULT 'ready'",
            "section_title": "TEXT",
            "char_start": "INTEGER",
            "char_end": "INTEGER",
        },
    }
    with sqlite3.connect(_sqlite_path) as conn:
        existing_tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            )
        }
        for table, table_columns in columns.items():
            if table not in existing_tables:
                continue
            existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            for name, definition in table_columns.items():
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        try:
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts "
                "USING fts5(chunk_id UNINDEXED, document_id UNINDEXED, source UNINDEXED, search_text)"
            )
        except sqlite3.Error as exc:
            logger.warning(f"SQLite FTS5 初始化失败，关键词路将降级: {exc}")
        conn.commit()


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def build_runtime(sqlite_path: str):
    """为测试或隔离进程创建独立数据库 runtime。"""
    path = os.path.abspath(sqlite_path)
    runtime_engine = _build_engine(path)
    runtime_session = async_sessionmaker(runtime_engine, class_=AsyncSession, expire_on_commit=False)
    return runtime_engine, runtime_session


async def get_db() -> AsyncSession:
    """获取数据库会话（FastAPI 依赖注入）"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """显式初始化数据库表和兼容 FTS schema。"""
    os.makedirs(os.path.dirname(_sqlite_path), exist_ok=True)
    _ensure_sqlite_schema_sync()
    # 导入所有模型确保注册
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 轻量列迁移：create_all 不会 ALTER 旧表，旧库缺列时这里补齐
        await _ensure_columns(conn, "spots", {"lng": "REAL", "lat": "REAL"})
        await _ensure_columns(conn, "avatar_presets", {
            "app_id": "TEXT DEFAULT ''",
            "app_secret": "TEXT DEFAULT ''",
        })
        await _ensure_columns(conn, "interactions", {
            "user_id": "TEXT",
            "emotion_score": "REAL DEFAULT 0.5",
            "citations_json": "TEXT DEFAULT '[]'",
            "retrieval_json": "TEXT DEFAULT '{}'",
            "trace_id": "TEXT DEFAULT ''",
            "spot_id": "TEXT",
        })
        await _ensure_columns(conn, "documents", {
            "storage_key": "TEXT",
            "content_sha256": "TEXT",
            "index_version": "TEXT DEFAULT 'hybrid-v1'",
            "error_message": "TEXT",
        })
        await _ensure_columns(conn, "chunks", {
            "normalized_content": "TEXT",
            "search_text": "TEXT",
            "content_sha256": "TEXT",
            "vector_id": "TEXT",
            "index_version": "TEXT DEFAULT 'hybrid-v1'",
            "status": "TEXT DEFAULT 'ready'",
            "section_title": "TEXT",
            "char_start": "INTEGER",
            "char_end": "INTEGER",
        })
        await _ensure_fts_table(conn)
        await _ensure_indexes(conn)
    logger.info("数据库表初始化完成")


async def _ensure_fts_table(conn):
    """创建 FTS5 关键词索引；SQLite 不支持时保留向量路。"""
    from sqlalchemy import text

    def _sync(sync_conn):
        sync_conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts "
            "USING fts5(chunk_id UNINDEXED, document_id UNINDEXED, source UNINDEXED, search_text)"
        ))

    try:
        await conn.run_sync(_sync)
    except Exception as exc:
        logger.warning(f"SQLite FTS5 初始化失败，关键词路将降级: {exc}")


async def _ensure_indexes(conn):
    """为旧 SQLite 补充常用查询索引；已存在时保持幂等。"""
    from sqlalchemy import text

    def _sync(sync_conn):
        statements = (
            "CREATE INDEX IF NOT EXISTS ix_documents_content_sha256 ON documents(content_sha256)",
            "CREATE INDEX IF NOT EXISTS ix_chunks_document_id ON chunks(document_id)",
            "CREATE INDEX IF NOT EXISTS ix_faqs_intent ON faqs(intent)",
            "CREATE INDEX IF NOT EXISTS ix_faqs_status ON faqs(status)",
            "CREATE INDEX IF NOT EXISTS ix_interactions_user_id ON interactions(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_interactions_spot_id ON interactions(spot_id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_favorites_user_type_item "
            "ON favorites(user_id, item_type, item_id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_visit_records_user_type_item "
            "ON visit_records(user_id, item_type, item_id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_reads_notice_user "
            "ON notification_reads(notification_id, user_id)",
        )
        for statement in statements:
            try:
                sync_conn.execute(text(statement))
            except Exception as exc:
                # 旧库可能缺表或有历史重复；保留数据并记录迁移警告。
                logger.warning(f"SQLite 索引兼容升级跳过: {exc}")

    await conn.run_sync(_sync)


async def _ensure_columns(conn, table: str, columns: dict):
    """幂等给已有表追加列（SQLite ALTER TABLE ADD COLUMN）"""
    from sqlalchemy import text, inspect
    def _sync(conn):
        insp = inspect(conn)
        if table not in insp.get_table_names():
            return
        existing = {c["name"] for c in insp.get_columns(table)}
        for col, coltype in columns.items():
            if col not in existing:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {coltype}'))
    await conn.run_sync(_sync)
