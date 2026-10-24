# backend/app/routers/projetos_route.py
import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

# --- ajustar para os imports reais do projeto nexusflow ---
from backend.app.db.session import get_db
from backend.app.schemas.projeto_schema import PaginatedResponse, ProjetoOut
from backend.app.services.projeto_service import listar_projetos_paginados

router = APIRouter(prefix="/api", tags=["Projetos"])

@router.get("/projetos", response_model=PaginatedResponse[ProjetoOut])
async def listar_projetos(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1, description="Página atual (começa em 1)")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Itens por página (máx. 100)")] = 20,
    uf: Annotated[str | None, Query(description="Filtra por UF exata, ex: SP")] = None,
    status: Annotated[str | None, Query(description="Filtra pela fase do projeto, ex: Operação, Construção")] = None,
    origem: Annotated[str | None, Query(description="Filtra pela origem do dado/projeto")] = None,
    search: Annotated[str | None, Query(description="Busca parcial (case-insensitive) no nome do projeto")] = None,
    sort_by: Annotated[str, Query(description="Coluna base para ordenação")] = "criado_em",
    sort_desc: Annotated[bool, Query(description="Ordenação decrescente?")] = True,
) -> PaginatedResponse[ProjetoOut]:
    """Lista projetos de geração com paginação server-side, filtros e ordenação dinâmica."""
    
    # Chama o service passando a responsabilidade de banco de dados
    itens, total = await listar_projetos_paginados(
        db=db,
        page=page,
        size=size,
        uf=uf,
        status=status,
        origem=origem,
        search=search,
        sort_by=sort_by,
        sort_desc=sort_desc
    )

    pages = math.ceil(total / size) if total else 0

    return PaginatedResponse[ProjetoOut](
        items=itens,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )