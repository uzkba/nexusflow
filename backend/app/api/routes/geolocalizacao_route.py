from fastapi import APIRouter, Depends
from sqlalchemy import func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db

# Ajuste este import para o caminho real do seu módulo de models
from backend.app.model.models import GenerationProject
from backend.app.schemas.geolocalizacao_schema import GeolocalizacaoItem, GeolocalizacaoResponse

router = APIRouter(prefix="/api", tags=["Geolocalização"])


@router.get(
    "/geolocalizacao",
    response_model=GeolocalizacaoResponse,
    summary="Dados agregados de projetos por Município/UF para mapas",
    description=(
        "Agrega os projetos de geração por Município e UF, retornando a "
        "quantidade de projetos e a potência outorgada total em cada "
        "município. Como um projeto pode abranger mais de um município "
        "(campo `municipios` é uma lista), a potência total do projeto é "
        "contabilizada em cada município ao qual ele pertence — a soma "
        "entre municípios pode, portanto, ser maior que a soma real de "
        "potência da base. Registros com UF ou lista de municípios nulos "
        "são descartados para não quebrar o parse do JSON no mapa."
    ),
)
async def get_geolocalizacao(
    db: AsyncSession = Depends(get_db),
) -> GeolocalizacaoResponse:
    # Filtra ANTES do LATERAL JOIN, numa subquery: o WHERE da query externa
    # só roda depois que o LATERAL já tentou desempacotar cada linha, então
    # não adianta pra evitar erro em linhas com município nulo/inválido.
    #
    # Municipios=None em Python vira o literal JSON `null` no banco (não
    # SQL NULL) por padrão no SQLAlchemy/JSONB — por isso checamos as duas
    # coisas: isnot(None) (SQL NULL) e jsonb_typeof(...) == "array" (JSON
    # null, objeto ou string acidentalmente salvos na coluna).
    base = (
        select(
            GenerationProject.ceg,
            GenerationProject.uf,
            GenerationProject.municipios,
            GenerationProject.potencia_outorgada_kw,
        )
        .where(
            GenerationProject.uf.isnot(None),
            GenerationProject.municipios.isnot(None),
            func.jsonb_typeof(GenerationProject.municipios) == "array",
        )
        .subquery("base")
    )

    # jsonb_array_elements_text "desempacota" a lista de municípios de cada
    # projeto em uma linha por município, via LATERAL JOIN.
    municipio_expand = (
        func.jsonb_array_elements_text(base.c.municipios)
        .table_valued("municipio")
        .render_derived()  # força "AS anon_1(municipio)" no SQL — sem isso
        .lateral()          # o Postgres não sabe o nome da coluna expandida
    )

    stmt = (
        select(
            base.c.uf.label("uf"),
            municipio_expand.c.municipio.label("municipio"),
            func.count(func.distinct(base.c.ceg)).label(
                "quantidade_projetos"
            ),
            func.sum(base.c.potencia_outorgada_kw).label("potencia_total"),
        )
        .select_from(base)
        .join(municipio_expand, true())
        .group_by(base.c.uf, municipio_expand.c.municipio)
        .order_by(base.c.uf, municipio_expand.c.municipio)
    )

    resultado = await db.execute(stmt)
    resultados = resultado.all()

    dados = [
        GeolocalizacaoItem(
            uf=row.uf,
            municipio=row.municipio,
            quantidade_projetos=row.quantidade_projetos,
            potencia_total=float(row.potencia_total or 0),
        )
        for row in resultados
    ]

    return GeolocalizacaoResponse(total_municipios=len(dados), dados=dados)