"""fix logs foreign key

Revision ID: fix_logs_foreign_key
Revises: ded8457d3b7d
Create Date: 2025-05-05 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_logs_foreign_key'
down_revision: Union[str, None] = 'ded8457d3b7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Удаляем существующее ограничение внешнего ключа
    op.drop_constraint('logs_user_id_fkey', 'logs', type_='foreignkey')
    
    # Создаем новое ограничение с ON DELETE SET NULL
    op.create_foreign_key(
        'logs_user_id_fkey',
        'logs',
        'users',
        ['user_id'],
        ['telegram_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем новое ограничение
    op.drop_constraint('logs_user_id_fkey', 'logs', type_='foreignkey')
    
    # Восстанавливаем старое ограничение
    op.create_foreign_key(
        'logs_user_id_fkey',
        'logs',
        'users',
        ['user_id'],
        ['telegram_id']
    ) 