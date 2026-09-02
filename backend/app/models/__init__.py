"""数据库模型 — SQLite 兼容"""
import json
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid as _uuid


def _new_id() -> str:
    return _uuid.uuid4().hex


def _json_default(obj):
    """JSON 序列化默认值"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


class Interaction(Base):
    """交互记录"""
    __tablename__ = "interactions"

    id = Column(String(36), primary_key=True, default=lambda: __import__('uuid').uuid4().hex)
    session_id = Column(String(64), index=True, nullable=False)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=True, index=True)
    query_text = Column(Text, nullable=False)
    query_mode = Column(String(10), default="text")
    response_text = Column(Text, nullable=False)
    rag_sources = Column(Text, default="[]")          # JSON 字符串
    emotion_label = Column(String(10), default="neutral")
    emotion_score = Column(Float, default=0.5)          # 用户情绪分：0负向 / 0.5中性 / 1正向
    spot_id = Column(String(64), ForeignKey("spots.id"), nullable=True, index=True)
    thinking_time_ms = Column(Integer, default=0)
    citations_json = Column(Text, default="[]")
    retrieval_json = Column(Text, default="{}")
    trace_id = Column(String(64), default="")
    created_at = Column(DateTime, default=func.now(), index=True)

    @property
    def rag_sources_list(self) -> list:
        try:
            return json.loads(self.rag_sources)
        except Exception:
            return []

    @rag_sources_list.setter
    def rag_sources_list(self, val: list):
        self.rag_sources = json.dumps(val, ensure_ascii=False, default=_json_default)


class Document(Base):
    """知识文档"""
    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_content_sha256", "content_sha256"),)

    id = Column(String(64), primary_key=True, default=_new_id)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20))
    file_size = Column(Integer, default=0)
    status = Column(String(20), default="uploaded")
    chunk_count = Column(Integer, default=0)
    storage_key = Column(String(255), default="")
    content_sha256 = Column(String(64), default="")
    index_version = Column(String(64), default="hybrid-v1")
    error_message = Column(Text, default="")
    uploaded_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    """知识分块"""
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_index"),
        Index("ix_chunks_document_id", "document_id"),
    )

    id = Column(String(64), primary_key=True, default=_new_id)
    document_id = Column(String(64), ForeignKey("documents.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    normalized_content = Column(Text, default="")
    search_text = Column(Text, default="")
    content_sha256 = Column(String(64), default="")
    vector_id = Column(String(128), default="")
    index_version = Column(String(64), default="hybrid-v1")
    status = Column(String(20), default="ready")
    section_title = Column(String(255), default="")
    char_start = Column(Integer, nullable=True)
    char_end = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())

    document = relationship("Document", back_populates="chunks")


class FAQ(Base):
    """常见问答对"""
    __tablename__ = "faqs"

    id = Column(String(64), primary_key=True, default=_new_id)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    match_text = Column(Text)
    tags = Column(Text, default="[]")    # JSON
    entities = Column(Text, default="[]")
    intent = Column(String(100), default="general_intro")
    intent_keywords = Column(Text, default="[]")
    exact_questions = Column(Text, default="[]")
    normalized_question = Column(String(512), default="", index=True)
    content_sha256 = Column(String(64), default="", index=True)
    status = Column(String(20), default="active", index=True)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())

    @property
    def entities_list(self) -> list:
        try: return json.loads(self.entities or "[]")
        except Exception: return []

    @entities_list.setter
    def entities_list(self, val: list):
        self.entities = json.dumps(val if isinstance(val, list) else [], ensure_ascii=False)

    @property
    def intent_keywords_list(self) -> list:
        try: return json.loads(self.intent_keywords or "[]")
        except Exception: return []

    @intent_keywords_list.setter
    def intent_keywords_list(self, val: list):
        self.intent_keywords = json.dumps(val if isinstance(val, list) else [], ensure_ascii=False)

    @property
    def exact_questions_list(self) -> list:
        try: return json.loads(self.exact_questions or "[]")
        except Exception: return []

    @exact_questions_list.setter
    def exact_questions_list(self, val: list):
        self.exact_questions = json.dumps(val if isinstance(val, list) else [], ensure_ascii=False)

    @property
    def tags_list(self) -> list:
        try: return json.loads(self.tags)
        except: return []

    @tags_list.setter
    def tags_list(self, val: list):
        self.tags = json.dumps(val, ensure_ascii=False)


class User(Base):
    """用户"""
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=_new_id)
    phone = Column(String(11), unique=True, nullable=False, index=True)
    password = Column(String(64), nullable=False)
    nickname = Column(String(50), default="游客")
    role = Column(String(20), default="visitor", index=True)
    created_at = Column(DateTime, default=func.now())


class AvatarPreset(Base):
    """魔珐星云预设角色及其星云应用配置。"""
    __tablename__ = "avatar_presets"

    id = Column(String(64), primary_key=True, default=_new_id)
    preset_key = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    scene_label = Column(String(100), default="景区讲解")
    voice_label = Column(String(100), default="")
    performance_style = Column(String(100), default="")
    thumbnail_url = Column(String(255), default="")
    sort_order = Column(Integer, default=0)
    is_active = Column(Integer, default=0, index=True)
    app_id = Column(String(128), default="")
    app_secret = Column(Text, default="")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())


class DailyStats(Base):
    """每日运营统计"""
    __tablename__ = "daily_stats"

    date = Column(String(10), primary_key=True)
    total_sessions = Column(Integer, default=0)
    total_interactions = Column(Integer, default=0)
    avg_thinking_time_ms = Column(Float, default=0.0)
    positive_ratio = Column(Float, default=0.0)
    top_questions = Column(Text, default="[]")
    top_attractions = Column(Text, default="[]")


class DocumentVersion(Base):
    """可审计的文档版本，供后续 shadow index 使用。"""
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_no", name="uq_document_versions_document_no"),)

    id = Column(String(64), primary_key=True, default=_new_id)
    document_id = Column(String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False)
    source_sha256 = Column(String(64), nullable=False)
    normalized_sha256 = Column(String(64), default="")
    chunking_config_hash = Column(String(64), default="")
    state = Column(String(20), default="building", index=True)
    supersedes_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=func.now())
    activated_at = Column(DateTime, nullable=True)


class IndexManifest(Base):
    """索引命名空间和 active 状态；失败版本不得覆盖线上 active。"""
    __tablename__ = "index_manifests"

    id = Column(String(64), primary_key=True, default=_new_id)
    version = Column(String(64), unique=True, nullable=False)
    state = Column(String(20), default="building", index=True)
    vector_collection = Column(String(255), default="")
    fts_namespace = Column(String(255), default="")
    embedding_model = Column(String(255), default="")
    config_hash = Column(String(64), default="")
    chunk_count = Column(Integer, default=0)
    vector_count = Column(Integer, default=0)
    fts_count = Column(Integer, default=0)
    content_hash = Column(String(64), default="")
    created_at = Column(DateTime, default=func.now())
    activated_at = Column(DateTime, nullable=True)
    retired_at = Column(DateTime, nullable=True)


class IndexJob(Base):
    """索引任务状态，支持幂等、租约和失败重试。"""
    __tablename__ = "index_jobs"

    id = Column(String(64), primary_key=True, default=_new_id)
    idempotency_key = Column(String(255), unique=True, nullable=False)
    job_type = Column(String(50), nullable=False)
    target_version = Column(String(64), nullable=True)
    state = Column(String(20), default="queued", index=True)
    attempt = Column(Integer, default=0)
    lease_owner = Column(String(128), nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())


class UserPin(Base):
    """游客自定义地图标记（用于热力图分析）"""
    __tablename__ = "user_pins"

    id = Column(String(64), primary_key=True, default=_new_id)
    name = Column(String(100), nullable=False, default="")
    lng = Column(Float, nullable=False)
    lat = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now(), index=True)


class UserVisit(Base):
    """游客被动位置上报（点击景点标记时静默记录，用于密集度热力图）"""
    __tablename__ = "user_visits"

    id = Column(String(64), primary_key=True, default=_new_id)
    spot_id = Column(String(64), nullable=True, index=True)
    lng = Column(Float, nullable=False)
    lat = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now(), index=True)


# 显式导入子模块模型，确保 init_db 时建表
from app.models.favorite import Favorite  # noqa: E402,F401
from app.models.feedback import Feedback  # noqa: E402,F401
from app.models.notification import Notification, NotificationRead  # noqa: E402,F401
from app.models.route import Route  # noqa: E402,F401
from app.models.saved_route import SavedRoute  # noqa: E402,F401
from app.models.spot import Spot  # noqa: E402,F401
from app.models.visit_record import VisitRecord  # noqa: E402,F401
