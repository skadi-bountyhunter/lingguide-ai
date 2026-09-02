"""账号保存路线模型"""
import json

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class SavedRoute(Base):
    """用户账号下保存的路线。"""

    __tablename__ = "saved_routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    source = Column(String(20), default="manual")
    title = Column(String(200), nullable=False)
    duration = Column(String(50))
    spots = Column(Text, default="[]")
    tips = Column(Text)
    interests = Column(Text, default="[]")
    citations = Column(Text, default="[]")
    retrieval = Column(Text, default="{}")
    trace_id = Column(String(64), default="")
    index_version = Column(String(64), default="")
    created_at = Column(DateTime, server_default=func.now())

    @property
    def spots_list(self) -> list:
        """安全读取景点 JSON 列表。"""
        try:
            value = json.loads(self.spots or "[]")
            return value if isinstance(value, list) else []
        except (TypeError, json.JSONDecodeError):
            return []

    @spots_list.setter
    def spots_list(self, value: list) -> None:
        """安全写入景点 JSON 列表。"""
        self.spots = json.dumps(
            value if isinstance(value, list) else [], ensure_ascii=False
        )

    @property
    def interests_list(self) -> list:
        """安全读取兴趣 JSON 列表。"""
        try:
            value = json.loads(self.interests or "[]")
            return value if isinstance(value, list) else []
        except (TypeError, json.JSONDecodeError):
            return []

    @interests_list.setter
    def interests_list(self, value: list) -> None:
        """安全写入兴趣 JSON 列表。"""
        self.interests = json.dumps(
            value if isinstance(value, list) else [], ensure_ascii=False
        )
