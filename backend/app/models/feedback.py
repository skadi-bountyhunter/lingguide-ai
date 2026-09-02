"""游客意见反馈模型。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Feedback(Base):
    """游客提交并由管理员处理的反馈。"""

    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    category = Column(String(20), nullable=False, default="suggestion", index=True)
    content = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    admin_reply = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
