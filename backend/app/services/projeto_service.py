# backend/app/services/projeto_service.py
from typing import Sequence, Tuple
from sqlalchemy import func, select, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession

# --- Ajuste o import do model para o caminho real ---
from backend.app.model.models import GenerationProject

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
    search: str | None
):
    """Aplica, de forma dinâmica, apenas os filtros que vierem preenchidos."""
    valores = {"uf": uf, "status": status, "origem": origem}
    for nome, valor in valores.items():
        if valor is not None:
            coluna = FILTROS_EXATOS[nome]
            stmt = stmt.where(coluna == valor)

    if search:
        stmt = stmt.where(GenerationProject.nome_projeto.ilike(f"%{search}%"))

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
    sort_desc: bool = True
) -> Tuple[Sequence[GenerationProject], int]:
    
    base_stmt = select(GenerationProject)
    base_stmt = _aplicar_filtros(base_stmt, uf, status, origem, search)

    # Contagem total otimizada pela PK
    count_stmt = select(func.count(GenerationProject.ceg))
    count_stmt = _aplicar_filtros(count_stmt, uf, status, origem, search)
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