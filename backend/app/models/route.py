"""路线模型 — 游客端预设经典路线（后台可编辑）"""
import json
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Route(Base):
    """预设经典路线"""
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, unique=True, nullable=False)       # 路线名
    icon = Column(String, default="📍")                        # 图标 emoji
    duration = Column(String, default="")                      # 游览时长，如 "3.5h"
    distance = Column(String, default="")                      # 路程，如 "4.2km"
    difficulty = Column(String, default="")                    # 难度：轻松/适中
    desc = Column(Text, default="")                            # 简介
    spots = Column(Text, default="[]")                         # JSON 数组：包含的景点名
    tags = Column(Text, default="[]")                          # JSON 数组：分类标签
    tip = Column(Text, default="")                             # 贴士
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ---- JSON list 字段的便捷读写 ----
    @property
    def spots_list(self) -> list:
        try:
            return json.loads(self.spots)
        except Exception:
            return []

    @spots_list.setter
    def spots_list(self, val: list):
        self.spots = json.dumps(val, ensure_ascii=False)

    @property
    def tags_list(self) -> list:
        try:
            return json.loads(self.tags)
        except Exception:
            return []

    @tags_list.setter
    def tags_list(self, val: list):
        self.tags = json.dumps(val, ensure_ascii=False)
