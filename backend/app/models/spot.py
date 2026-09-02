"""景点模型 — 景点详情卡片内容（后台可编辑）"""
import json
from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from app.core.database import Base


class Spot(Base):
    """景区景点"""
    __tablename__ = "spots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)  # 景点名（路由参数用）
    icon = Column(String, default="")
    image = Column(String, default="")           # 图片 URL
    desc = Column(String, default="")            # 首页短描述
    full_desc = Column(Text, default="")         # 详情完整介绍（段落以 \n\n 分隔）
    tags = Column(Text, default="[]")            # JSON 数组
    duration = Column(String, default="")
    distance = Column(String, default="")
    highlights = Column(Text, default="[]")      # JSON 数组
    hours = Column(String, default="")
    ticket = Column(String, default="")
    tips = Column(Text, default="[]")            # JSON 数组
    best_season = Column(String, default="")
    nearby = Column(Text, default="[]")          # JSON 数组（周边景点名）
    lng = Column(Float, nullable=True)           # 经度（高德 GCJ-02 坐标）
    lat = Column(Float, nullable=True)           # 纬度
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ---- JSON list 字段的便捷读写 ----
    @property
    def tags_list(self) -> list:
        try:
            return json.loads(self.tags)
        except Exception:
            return []

    @tags_list.setter
    def tags_list(self, val: list):
        self.tags = json.dumps(val, ensure_ascii=False)

    @property
    def highlights_list(self) -> list:
        try:
            return json.loads(self.highlights)
        except Exception:
            return []

    @highlights_list.setter
    def highlights_list(self, val: list):
        self.highlights = json.dumps(val, ensure_ascii=False)

    @property
    def tips_list(self) -> list:
        try:
            return json.loads(self.tips)
        except Exception:
            return []

    @tips_list.setter
    def tips_list(self, val: list):
        self.tips = json.dumps(val, ensure_ascii=False)

    @property
    def nearby_list(self) -> list:
        try:
            return json.loads(self.nearby)
        except Exception:
            return []

    @nearby_list.setter
    def nearby_list(self, val: list):
        self.nearby = json.dumps(val, ensure_ascii=False)
