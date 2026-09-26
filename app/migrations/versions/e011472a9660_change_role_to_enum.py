"""change role to enum

Revision ID: e011472a9660
Revises: fdbaee67ddee
Create Date: 2026-09-26 23:10:46.453452

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e011472a9660"
down_revision: str | Sequence[str] | None = "fdbaee67ddee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Создаём тип ENUM (если ещё нет)
    user_role_enum = sa.Enum("admin", "seller", "buyer", name="user_role")
    user_role_enum.create(op.get_bind(), checkfirst=True)

    # 2. Конвертируем колонку с явным USING
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE user_role USING role::user_role")


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Обратно в VARCHAR
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR USING role::VARCHAR")

    # 2. Удаляем тип
    user_role_enum = sa.Enum("admin", "seller", "buyer", name="user_role")
    user_role_enum.drop(op.get_bind(), checkfirst=True)
