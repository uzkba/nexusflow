"""removido_da_fonte

Revision ID: 7aa36ef5f5b3
Revises: 0288f9610252
Create Date: 2026-11-14 10:51:00.592810

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7aa36ef5f5b3'
down_revision: Union[str, Sequence[str], None] = '0288f9610252'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "projetos_geracao",
        sa.Column("removido_da_fonte_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "projetos_geracao",
        sa.Column("motivo_remocao", sa.String(30), nullable=True),
    )
    op.create_index("ix_projetos_removido", "projetos_geracao", ["removido_da_fonte_em"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_projetos_removido", table_name="projetos_geracao")
    op.drop_column("projetos_geracao", "motivo_remocao")
    op.drop_column("projetos_geracao", "removido_da_fonte_em")
