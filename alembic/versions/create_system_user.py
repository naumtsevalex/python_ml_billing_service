"""create system user

Revision ID: create_system_user
Revises: ded8457d3b7d
Create Date: 2025-05-05 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = 'create_system_user'
down_revision: Union[str, None] = 'ded8457d3b7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем системного пользователя
    op.execute(
        """
        INSERT INTO users (telegram_id, username, created_at, is_active)
        VALUES (-1, 'system', CURRENT_TIMESTAMP, true)
        ON CONFLICT (telegram_id) DO NOTHING;
        """
    )
    
    # Добавляем баланс для системного пользователя
    op.execute(
        """
        INSERT INTO balances (user_id, balance, updated_at)
        VALUES (-1, 0, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id) DO NOTHING;
        """
    )

def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем баланс системного пользователя
    op.execute("DELETE FROM balances WHERE user_id = -1;")
    
    # Удаляем системного пользователя
    op.execute("DELETE FROM users WHERE telegram_id = -1;") 