# backend/app/services/projeto_service.py
from typing import Sequence, Tuple
from uuid import UUID

from fastapi import HTTPException, status

from sqlalchemy import func, select, asc, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

# --- Ajuste o import do model para o caminho real ---
from backend.app.model.models import GenerationProject
from backend.app.schemas.filtros_schema import normalizar_origem, padrao_contem

FILTROS_EXATOS = {
    "uf": GenerationProject.uf,
    "status": GenerationProject.fase,
    "origem": GenerationProject.origem,
}

def _aplicar_filtros(
    stmt, 
    uf: str | None, 
    status: str | None, 
    origem: str | None, 
    search: str | None,
    nome: str | None = None,
    cliente: str | None = None,
    municipio: str | None = None,
    ano: str | None = None,
):
    """Aplica, de forma dinâmica, apenas os filtros que vierem preenchidos."""
    # Normaliza antes de comparar: o banco guarda 'Solar' / 'Eólica' e a
    # comparação é exata, então 'solar' ou 'eolica' devolveriam lista vazia.
    valores = {
        "uf": uf.strip().upper() if uf else None,
        "status": status,
        "origem": normalizar_origem(origem),
    }
    for nome_filtro, valor in valores.items():
        # Texto vazio ("") também significa "sem filtro"
        if valor:
            coluna = FILTROS_EXATOS[nome_filtro]
            stmt = stmt.where(coluna == valor)

    # Busca parcial, sem diferenciar maiúsculas, no nome do projeto.
    # `search` (campo da tabela) e `nome` (sidebar) podem vir juntos: ambos se aplicam.
    for termo in (search, nome):
        if termo and termo.strip():
            stmt = stmt.where(
                GenerationProject.nome_projeto.ilike(padrao_contem(termo), escape="\\")
            )

    # Demais filtros da sidebar. Valores vazios ou inválidos são ignorados, e não viram 422.
    if cliente:
        try:
            stmt = stmt.where(GenerationProject.cliente_id == UUID(cliente))
        except ValueError:
            pass
    if municipio:
        # municipios é JSONB list[str]: contenção (@>), não igualdade
        stmt = stmt.where(GenerationProject.municipios.contains([municipio]))
    if ano and ano.strip().isdigit():
        stmt = stmt.where(GenerationProject.inicio_vigencia_ano == int(ano))

    # REGRA CRÍTICA: Não adicionamos nenhum filtro sobre `status_revisao`.
    # Todos os projetos devem retornar independentemente se estão pendentes ou aprovados.
    
    return stmt

async def listar_projetos_paginados(
    db: AsyncSession,
    page: int,
    size: int,
    uf: str | None = None,
    status: str | None = None,
    origem: str | None = None,
    search: str | None = None,
    sort_by: str = "criado_em",
    sort_desc: bool = True,
    nome: str | None = None,
    cliente: str | None = None,
    municipio: str | None = None,
    ano: str | None = None,
) -> Tuple[Sequence[GenerationProject], int]:
    
    base_stmt = select(GenerationProject)
    base_stmt = _aplicar_filtros(base_stmt, uf, status, origem, search, nome, cliente, municipio, ano)

    # Contagem total otimizada pela PK
    count_stmt = select(func.count(GenerationProject.ceg))
    count_stmt = _aplicar_filtros(count_stmt, uf, status, origem, search, nome, cliente, municipio, ano)
    total = (await db.scalar(count_stmt)) or 0

    # Ordenação Dinâmica
    sort_column = getattr(GenerationProject, sort_by, GenerationProject.criado_em)
    order_func = desc if sort_desc else asc
    
    # Offset e Limit (Paginação)
    offset = (page - 1) * size
    data_stmt = (
        base_stmt.order_by(order_func(sort_column), GenerationProject.ceg.asc())
        .offset(offset)
        .limit(size)
    )
    
    resultado = await db.execute(data_stmt)
    itens = resultado.scalars().all()

    return itens, total

async def vincular_cliente(db: AsyncSession, ceg: str, cliente_id: str) -> dict:
    stmt = (
        update(GenerationProject)
        .where(GenerationProject.ceg == ceg)
        .values(cliente_id=cliente_id)
    )

    resultado = await db.execute(stmt)

    if resultado.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projeto com CEG {ceg} não encontrado."
        )

    await db.commit()
    return {"mensagem": "Cliente vinculado com sucesso", "ceg": ceg}