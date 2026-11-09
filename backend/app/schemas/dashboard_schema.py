"""
Schemas de resposta para os endpoints analíticos (KPIs e Gráficos).

Task: "Endpoints de KPIs e Gráficos" — nexusflow
"""
from decimal import Decimal
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KPIsResponse(BaseModel):
    """Totalizadores gerais exibidos no topo do Painel Executivo."""

    total_projetos: int = Field(..., description="Quantidade total de projetos do portfólio")
    potencia_total_mw: Decimal = Field(..., description="Soma da potência outorgada, em MW")
    total_clientes: int = Field(
        ..., description="Quantidade de clientes reais distintos (exclui o sentinela)"
    )
    projetos_pendentes_revisao: int = Field(
        ..., description="Projetos cujo status_revisao ainda está pendente "
                         "(informativo — NÃO são excluídos dos totais acima)"
    )
    projetos_sem_proprietario: int = Field(
        ..., description="Projetos sem cliente consolidado (cliente_id nulo ou sentinela)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_projetos": 1904,
                "potencia_total_mw": "81928.51",
                "total_clientes": 87,
                "projetos_pendentes_revisao": 34,
                "projetos_sem_proprietario": 1200,
            }
        }
    )


class PotenciaPorUFItem(BaseModel):
    """Um ponto do gráfico de Potência por UF."""

    uf: str = Field(..., description="Sigla da Unidade Federativa (ex: 'SP', 'CE')")
    potencia_total: Decimal = Field(..., description="Soma da potência outorgada na UF, em MW")
    total_projetos: int = Field(..., description="Quantidade de projetos na UF")


class PotenciaPorUFResponse(BaseModel):
    dados: List[PotenciaPorUFItem]


class EvolucaoAnualItem(BaseModel):
    """Um ponto do gráfico de Evolução Anual."""

    ano: int = Field(..., description="Ano de referência (ano de operação/outorga)")
    potencia_total: Decimal = Field(..., description="Soma da potência outorgada no ano, em MW")
    total_projetos: int = Field(..., description="Quantidade de projetos no ano")
    potencia_acumulada: Decimal = Field(
        ..., description="Potência acumulada até o ano (soma corrida, para curva de evolução)"
    )


class EvolucaoAnualResponse(BaseModel):
    dados: List[EvolucaoAnualItem]


class OrigemItem(BaseModel):
    """Um ponto do gráfico Matriz de Geração (Solar x Eólica)."""

    origem: str | None = Field(None, description="Tipo de geração: 'Solar' ou 'Eólica'")
    potencia_total_mw: float = Field(..., description="Soma da potência outorgada, em MW")
    total_projetos: int = Field(..., description="Quantidade de projetos da origem")


class OrigemResponse(BaseModel):
    dados: List[OrigemItem]


class RankingClienteItem(BaseModel):
    """Um item do ranking de clientes por potência."""

    cliente_id: UUID
    nome_oficial: str
    potencia_total_mw: float = Field(..., description="Soma da potência outorgada, em MW")
    total_projetos: int


class RankingClientesResponse(BaseModel):
    dados: List[RankingClienteItem]


class ProjetoSemProprietarioItem(BaseModel):
    """Um item da lista de projetos órfãos para o radar de prospecção."""

    ceg: str = Field(..., description="Código Único ANEEL")
    nome_projeto: str = Field(..., description="Nome do projeto de geração")
    uf: str | None = Field(None, description="Unidade Federativa")
    potencia_mw: float = Field(..., description="Potência outorgada convertida para MW")
    fase: str | None = Field(None, description="Fase atual do projeto")


class ProjetosSemProprietarioResponse(BaseModel):
    """Resposta contendo a lista de projetos sem proprietário."""
    
    dados: List[ProjetoSemProprietarioItem]