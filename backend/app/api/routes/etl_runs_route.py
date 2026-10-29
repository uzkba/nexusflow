from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.model.models import EtlRun
from backend.app.schemas.etl_run_schema import PaginatedEtlRunResponse

# Ajuste para importar sua dependência real de injeção do banco de dados
# ex: from app.db.session import get_db
from backend.app.db.session import get_db

router = APIRouter(prefix="/etl-runs", tags=["ETL Observability"])

@router.get("", response_model=PaginatedEtlRunResponse)
async def get_etl_runs(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(10, ge=1, le=100, description="Itens por página")
):
    offset = (page - 1) * size

    total_query = await db.execute(select(func.count()).select_from(EtlRun))
    total_records = total_query.scalar_one()

    stmt = (
        select(EtlRun)
        .order_by(EtlRun.iniciado_em.desc())
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    total_pages = (total_records + size - 1) // size

    return PaginatedEtlRunResponse(
        items=list(items),
        total=total_records,
        page=page,
        size=size,
        total_pages=total_pages
    )