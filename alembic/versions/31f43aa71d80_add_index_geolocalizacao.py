"""add index on uf and GIN index on municipios for geolocalizacao aggregation

Revision ID: xxxx_add_index_geolocalizacao
Revises: <coloque_aqui_a_revisao_anterior>
Create Date: 2026-09-22
"""
from alembic import op
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '31f43aa71d80'
down_revision: Union[str, Sequence[str], None] = '049999ce6237'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # uf já tem index=True no model, mas garanta que a migration existente
    # o criou; se sim, remova esta linha para não duplicar.
    op.create_index(
        "ix_projetos_geracao_uf",
        "projetos_geracao",
        ["uf"],
        if_not_exists=True,
    )

    # municipios é JSONB (lista) — um índice GIN acelera buscas de
    # contenção (@>, ?) nessa coluna. Ele NÃO acelera diretamente o
    # LATERAL JOIN com jsonb_array_elements_text usado no agrupamento,
    # mas ajuda outras queries que filtrem por município específico.
    op.create_index(
        "ix_projetos_geracao_municipios_gin",
        "projetos_geracao",
        ["municipios"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_projetos_geracao_municipios_gin", table_name="projetos_geracao")
    op.drop_index("ix_projetos_geracao_uf", table_name="projetos_geracao")