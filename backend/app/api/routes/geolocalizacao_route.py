from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, true, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.model.models import Client, GenerationProject, RawName

# Importando o teu schema unificado
from backend.app.schemas.geolocalizacao_schema import (
    GeolocalizacaoResponse, 
    GeolocalizacaoItem
)
from backend.app.schemas.filtros_schema import FiltrosQuery
# Mesmas condições de filtro da sidebar usadas na Visão Geral (regra em um só lugar)
from backend.app.services.dashboard_service import _condicoes as condicoes_filtros

router = APIRouter(prefix="/api", tags=["Geolocalização"])

@router.get(
    "/geolocalizacao",
    response_model=GeolocalizacaoResponse,
    summary="Dados geográficos agregados para Mapa e Ranking",
    description=(
        "Agrega os projetos utilizando LATERAL JOIN para desempacotar o JSONB. "
        "Retorna a quantidade de projetos, potência total e as coordenadas médias "
        "do município para plotagem no ECharts. Projetos sem coordenadas são ignorados. "
        "Aceita os mesmos filtros da sidebar (origem, cliente, nome, uf, municipio, ano)."
    ),
)
async def get_geolocalizacao(
    filtros: Annotated[FiltrosQuery, Query()],
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
            # Filtros da sidebar (origem, cliente, nome, uf, municipio, ano)
            *condicoes_filtros(filtros),
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

    # Com filtro de município, um projeto que cobre vários municípios não deve
    # gerar linhas dos outros municípios dele.
    if filtros.municipio:
        stmt = stmt.where(municipio_expand.c.municipio == filtros.municipio)

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


class ProjetoDoMunicipio(BaseModel):
    ceg: str
    nome_projeto: str | None = None
    origem: str | None = None  # tipo: 'Solar' ou 'Eólica'
    fase: str | None = None
    potencia_outorgada_kw: float | None = None
    inicio_vigencia_ano: int | None = None
    status_revisao: str | None = None
    # Proprietário como veio da ANEEL (nome bruto principal do projeto)
    proprietario: str | None = None
    # Cliente consolidado (vazio até o admin aprovar a consolidação)
    cliente_nome: str | None = None


class ProjetosDoMunicipioResponse(BaseModel):
    municipio: str
    total: int
    dados: list[ProjetoDoMunicipio]


# Segurança: nenhum município hoje passa de ~100 projetos; o teto evita respostas enormes.
LIMITE_PROJETOS_POR_MUNICIPIO = 500


@router.get(
    "/geolocalizacao/projetos",
    response_model=ProjetosDoMunicipioResponse,
    summary="Projetos de um município (detalhe do Ranking de Municípios)",
    description=(
        "Lista os projetos que compõem a contagem de um município no ranking. "
        "Informe `municipio` (texto exato do ranking, ex.: 'Bom Jesus da Lapa - BA') e, "
        "opcionalmente, `uf` e os demais filtros da sidebar. Usa as mesmas regras do ranking "
        "(projetos sem coordenadas são ignorados), então a quantidade bate com a da tabela."
    ),
)
async def get_projetos_do_municipio(
    filtros: Annotated[FiltrosQuery, Query()],
    db: AsyncSession = Depends(get_db),
) -> ProjetosDoMunicipioResponse:
    if not filtros.municipio:
        raise HTTPException(status_code=422, detail="Informe o município")

    stmt = (
        select(
            GenerationProject.ceg,
            GenerationProject.nome_projeto,
            GenerationProject.origem,
            GenerationProject.fase,
            GenerationProject.potencia_outorgada_kw,
            GenerationProject.inicio_vigencia_ano,
            GenerationProject.status_revisao,
            RawName.nome_bruto.label("proprietario"),
            Client.nome_oficial.label("cliente_nome"),
        )
        .select_from(GenerationProject)
        .outerjoin(RawName, RawName.id == GenerationProject.nome_bruto_principal_id)
        .outerjoin(Client, Client.id == GenerationProject.cliente_id)
        .where(
            GenerationProject.uf.isnot(None),
            GenerationProject.municipios.isnot(None),
            func.jsonb_typeof(GenerationProject.municipios) == "array",
            # Mesmas regras do ranking, para a contagem bater
            GenerationProject.latitude.isnot(None),
            GenerationProject.longitude.isnot(None),
            # Filtros da sidebar, incluindo uf e município (contido na lista de municípios)
            *condicoes_filtros(filtros),
        )
        .order_by(
            desc(GenerationProject.potencia_outorgada_kw).nulls_last(),
            GenerationProject.nome_projeto.asc(),
            GenerationProject.ceg.asc(),
        )
        .limit(LIMITE_PROJETOS_POR_MUNICIPIO)
    )

    linhas = (await db.execute(stmt)).all()
    dados = [
        ProjetoDoMunicipio(
            ceg=r.ceg,
            nome_projeto=r.nome_projeto,
            origem=r.origem,
            fase=r.fase,
            potencia_outorgada_kw=float(r.potencia_outorgada_kw)
            if r.potencia_outorgada_kw is not None
            else None,
            inicio_vigencia_ano=r.inicio_vigencia_ano,
            status_revisao=r.status_revisao.value if r.status_revisao is not None else None,
            proprietario=r.proprietario,
            cliente_nome=r.cliente_nome,
        )
        for r in linhas
    ]
    return ProjetosDoMunicipioResponse(municipio=filtros.municipio, total=len(dados), dados=dados)