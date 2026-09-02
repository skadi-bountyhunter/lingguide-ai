"""建立星云数字人角色预设表。"""
from alembic import op
import sqlalchemy as sa

revision = "0002_avatar_presets"
down_revision = "0001_rag_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "avatar_presets",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("preset_key", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("scene_label", sa.String(100), server_default="景区讲解"),
        sa.Column("voice_label", sa.String(100), server_default=""),
        sa.Column("performance_style", sa.String(100), server_default=""),
        sa.Column("thumbnail_url", sa.String(255), server_default=""),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("ix_avatar_presets_preset_key", "avatar_presets", ["preset_key"])
    op.create_index("ix_avatar_presets_is_active", "avatar_presets", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_avatar_presets_is_active", table_name="avatar_presets")
    op.drop_index("ix_avatar_presets_preset_key", table_name="avatar_presets")
    op.drop_table("avatar_presets")
