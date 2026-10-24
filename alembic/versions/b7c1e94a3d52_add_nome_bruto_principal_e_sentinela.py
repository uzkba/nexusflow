"""add nome_bruto_principal_id em projetos_geracao e cliente sentinela

Revision ID: b7c1e94a3d52
Revises: 31f43aa71d80
Create Date: 2026-10-19 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1e94a3d52'
down_revision: Union[str, Sequence[str], None] = '31f43aa71d80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Valor LITERAL de propósito: uma migration não pode mudar se a constante do
# app mudar depois. Deve ser igual a SENTINELA_CLIENTE_ID em
# backend/app/core/constantes.py (backend/tests/test_constantes.py garante).
SENTINELA_CLIENTE_ID = "00000000-0000-0000-0000-000000000001"
SENTINELA_NOME = "Não Informado"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "projetos_geracao",
        sa.Column("nome_bruto_principal_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_projetos_geracao_nome_bruto_principal",
        "projetos_geracao",
        "nomes_brutos",
        ["nome_bruto_principal_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_projetos_geracao_nome_bruto_principal_id",
        "projetos_geracao",
        ["nome_bruto_principal_id"],
    )

    # Cliente sentinela para obras cujo proprietário o SIGA não informa.
    # Idempotente: reexecutar a migration não duplica nem falha.
    op.execute(
        f"INSERT INTO clientes (id, nome_oficial) "
        f"VALUES ('{SENTINELA_CLIENTE_ID}'::uuid, '{SENTINELA_NOME}') "
        f"ON CONFLICT (id) DO NOTHING"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_projetos_geracao_nome_bruto_principal_id",
        table_name="projetos_geracao",
    )
    op.drop_constraint(
        "fk_projetos_geracao_nome_bruto_principal",
        "projetos_geracao",
        type_="foreignkey",
    )
    op.drop_column("projetos_geracao", "nome_bruto_principal_id")

    # Só remove o sentinela se nada o referencia (não apaga dado de negócio).
    op.execute(
        f"DELETE FROM clientes c "
        f"WHERE c.id = '{SENTINELA_CLIENTE_ID}'::uuid "
        f"AND NOT EXISTS (SELECT 1 FROM projetos_geracao p WHERE p.cliente_id = c.id) "
        f"AND NOT EXISTS (SELECT 1 FROM nomes_brutos n WHERE n.cliente_id = c.id) "
        f"AND NOT EXISTS (SELECT 1 FROM consolidacoes_pendentes q "
        f"WHERE q.cliente_sugerido_id = c.id)"
    )