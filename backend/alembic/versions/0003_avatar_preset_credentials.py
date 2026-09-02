"""为星云角色预设增加应用凭据。"""
from alembic import op
import sqlalchemy as sa

revision = "0003_avatar_preset_credentials"
down_revision = "0002_avatar_presets"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("avatar_presets", "app_id"):
        op.add_column("avatar_presets", sa.Column("app_id", sa.String(128), server_default=""))
    if not _has_column("avatar_presets", "app_secret"):
        op.add_column("avatar_presets", sa.Column("app_secret", sa.Text(), server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("avatar_presets") as batch_op:
        if _has_column("avatar_presets", "app_secret"):
            batch_op.drop_column("app_secret")
        if _has_column("avatar_presets", "app_id"):
            batch_op.drop_column("app_id")
