"""收藏模型。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class Favorite(Base):
    """登录用户收藏的景点或路线。"""

    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "item_type", "item_id", name="uq_favorites_user_type_item"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    item_type = Column(String(20), nullable=False)
    item_id = Column(String(100), nullable=False)
    item_name = Column(String(200), nullable=False)
    item_cover = Column(String(500), default="")
    created_at = Column(DateTime, server_default=func.now())
