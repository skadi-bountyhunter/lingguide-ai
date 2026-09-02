"""消息通知及用户已读关系模型。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class Notification(Base):
    """全体通知或指定用户通知。"""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(20), nullable=False, default="system", index=True)
    target_user_id = Column(String(64), ForeignKey("users.id"), nullable=True, index=True)
    created_by = Column(String(64), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)


class NotificationRead(Base):
    """每个用户独立记录通知已读状态。"""

    __tablename__ = "notification_reads"
    __table_args__ = (
        UniqueConstraint(
            "notification_id", "user_id", name="uq_notification_reads_notice_user"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_id = Column(
        Integer, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    read_at = Column(DateTime, server_default=func.now(), nullable=False)
