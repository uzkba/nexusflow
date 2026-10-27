from fastapi import APIRouter, Depends
from sqlalchemy import func, select, true, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.model.models import GenerationProject

# Importando o teu schema unificado
from backend.app.schemas.geolocalizacao_schema import (
    GeolocalizacaoResponse, 
    GeolocalizacaoItem
)

router = APIRouter(prefix="/api", tags=["Geolocalização"])

@router.get(
    "/geolocalizacao",
    response_model=GeolocalizacaoResponse,
    summary="Dados geográficos agregados para Mapa e Ranking",
    description=(
        "Agrega os projetos utilizando LATERAL JOIN para desempacotar o JSONB. "
        "Retorna a quantidade de projetos, potência total e as coordenadas médias "
        "do município para plotagem no ECharts. Projetos sem coordenadas são ignorados."
    ),
)
async def get_geolocalizacao(
    db: AsyncSession = Depends(get_db),
) -> GeolocalizacaoResponse:
    
    # 1. Base com as colunas reais corrigidas (incluindo latitude e longitude)
    base = (
        select(
            GenerationProject.ceg,
            GenerationProject.uf,
            GenerationProject.municipios,
            GenerationProject.potencia_outorgada_kw,
            GenerationProject.latitude,
            GenerationProject.longitude,
        )
        .where(
            GenerationProject.uf.isnot(None),
            GenerationProject.municipios.isnot(None),
            func.jsonb_typeof(GenerationProject.municipios) == "array",
            # Filtros adicionados para ignorar os 66 projetos com coordenadas nulas:
            GenerationProject.latitude.isnot(None),
            GenerationProject.longitude.isnot(None),
        )
        .subquery("base")
    )

    # 2. Desempacota o array de municípios
    municipio_expand = (
        func.jsonb_array_elements_text(base.c.municipios)
        .table_valued("municipio")
        .render_derived()
        .lateral()
    )

    # 3. Query final unificada (Ranking + Coordenadas para o Mapa)
    stmt = (
        select(
            base.c.uf.label("uf"),
            municipio_expand.c.municipio.label("municipio"),
            func.count(func.distinct(base.c.ceg)).label("quantidade_projetos"),
            func.sum(base.c.potencia_outorgada_kw).label("potencia_total"),
            # Agregamos as coordenadas (média) para ter o ponto central do município
            func.avg(base.c.latitude).label("latitude"),
            func.avg(base.c.longitude).label("longitude"),
        )
        .select_from(base)
        .join(municipio_expand, true())
        .group_by(base.c.uf, municipio_expand.c.municipio)
        .order_by(desc("quantidade_projetos"))
    )

    resultado = await db.execute(stmt)
    resultados = resultado.all()

    # 4. Formata a resposta para o Pydantic
    dados = []
    for row in resultados:
        dados.append(
            GeolocalizacaoItem(
                uf=row.uf,
                municipio=row.municipio,
                quantidade_projetos=row.quantidade_projetos,
                potencia_total=float(row.potencia_total or 0.0),
                latitude=float(row.latitude or 0.0),
                longitude=float(row.longitude or 0.0)
            )
        )

    return GeolocalizacaoResponse(
        total_municipios=len(dados),
        dados=dados
    )