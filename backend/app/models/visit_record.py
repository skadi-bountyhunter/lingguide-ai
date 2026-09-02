"""用户游览足迹模型。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class VisitRecord(Base):
    """同一用户、类型和对象只保留一条累计足迹。"""

    __tablename__ = "visit_records"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "item_type", "item_id", name="uq_visit_records_user_type_item"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    item_type = Column(String(20), nullable=False, default="spot")
    item_id = Column(String(100), nullable=False)
    item_name = Column(String(200), nullable=False)
    item_cover = Column(String(500), default="")
    first_visited_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_visited_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    visit_count = Column(Integer, default=1, nullable=False)
