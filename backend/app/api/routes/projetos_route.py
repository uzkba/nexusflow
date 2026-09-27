"""
GET /api/projetos

Listagem paginada (server-side) de projetos de geração, com filtros
dinâmicos via query string.

Ajuste os imports abaixo para o caminho real no seu projeto:
    from app.database import get_db
    from app.models.projeto import GenerationProject
"""

import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# --- ajustar para os imports reais do projeto nexusflow ---
from backend.app.db.session import get_db
from backend.app.model import GenerationProject
from backend.app.schemas.projeto_schema import PaginatedResponse, ProjetoOut

router = APIRouter(prefix="/api", tags=["Projetos"])

# Mapeia o parâmetro de query -> coluna do model, para os filtros de
# igualdade exata. Centralizar aqui facilita alinhar com o frontend:
# qualquer filtro novo combinado com o Dev C é só adicionar uma linha.
#
# Nota: o model não tem coluna `status` — o campo que carrega valores
# como "Operação"/"Construção" é `fase`. O parâmetro de query continua
# se chamando `status` (alias) porque é o nome citado no contrato com o
# frontend; internamente ele filtra por `fase`. Se o time quiser expor
# `status_revisao` (fluxo de revisão pendente/aprovado) como filtro
# separado, adicione outra entrada aqui.
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
):
    """Aplica, de forma dinâmica, apenas os filtros que vierem preenchidos.

    Recebe o `stmt` (Select) e retorna o mesmo `stmt` com os `.where()`
    encadeados — usada tanto pela query de dados quanto pela de contagem,
    para garantir que os dois números (itens retornados x total) sejam
    sempre consistentes.
    """
    valores = {"uf": uf, "status": status, "origem": origem}
    for nome, valor in valores.items():
        if valor is not None:
            coluna = FILTROS_EXATOS[nome]
            stmt = stmt.where(coluna == valor)

    if search:
        # busca parcial, case-insensitive, no nome do projeto
        stmt = stmt.where(GenerationProject.nome_projeto.ilike(f"%{search}%"))

    return stmt


@router.get("/projetos", response_model=PaginatedResponse[ProjetoOut])
async def listar_projetos(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1, description="Página atual (começa em 1)")] = 1,
    size: Annotated[
        int, Query(ge=1, le=100, description="Itens por página (máx. 100)")
    ] = 20,
    uf: Annotated[str | None, Query(description="Filtra por UF exata, ex: SP")] = None,
    status: Annotated[
        str | None,
        Query(description="Filtra pela fase do projeto, ex: Operação, Construção"),
    ] = None,
    origem: Annotated[
        str | None, Query(description="Filtra pela origem do dado/projeto")
    ] = None,
    search: Annotated[
        str | None,
        Query(description="Busca parcial (case-insensitive) no nome do projeto"),
    ] = None,
) -> PaginatedResponse[ProjetoOut]:
    """Lista projetos de geração com paginação server-side e filtros dinâmicos.

    Parâmetros de paginação: `page` (1-based) e `size`.
    Filtros suportados: `uf`, `status` (mapeado para a coluna `fase`),
    `origem` (igualdade exata) e `search` (busca parcial no nome do
    projeto).

    Alinhar com o Dev C (frontend) se surgir necessidade de novos filtros
    (ex: faixa de potência, `inicio_vigencia_ano`, `cliente_id`) — basta
    estender `FILTROS_EXATOS` ou `_aplicar_filtros`.
    """
    base_stmt = select(GenerationProject)
    base_stmt = _aplicar_filtros(base_stmt, uf, status, origem, search)

    # --- contagem total otimizada ---
    # Evita fazer SELECT * e contar em Python: pede ao Postgres apenas o
    # número de linhas que atendem ao mesmo filtro, contando a PK (`ceg`),
    # que já é indexada por ser chave primária — evita ler as colunas
    # pesadas (municipios JSONB, diff_pendente JSONB etc.) só para contar.
    count_stmt = select(func.count(GenerationProject.ceg))
    count_stmt = _aplicar_filtros(count_stmt, uf, status, origem, search)
    total = (await db.scalar(count_stmt)) or 0

    # --- página de dados ---
    # Ordena por criado_em (mais recentes primeiro) com `ceg` como
    # tie-breaker: como `ceg` é string (não sequencial), sem uma segunda
    # coluna de ordenação o OFFSET/LIMIT pode duplicar ou pular linhas
    # quando várias têm o mesmo `criado_em`.
    offset = (page - 1) * size
    data_stmt = (
        base_stmt.order_by(
            GenerationProject.criado_em.desc(), GenerationProject.ceg.asc()
        )
        .offset(offset)
        .limit(size)
    )
    resultado = await db.execute(data_stmt)
    itens = resultado.scalars().all()

    pages = math.ceil(total / size) if total else 0

    return PaginatedResponse[ProjetoOut](
        items=itens,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )