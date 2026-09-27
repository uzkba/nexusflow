"""
Schemas de resposta para os endpoints analíticos (KPIs e Gráficos).

Task: "Endpoints de KPIs e Gráficos" — nexusflow
"""
from datetime import date
from decimal import Decimal
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class KPIsResponse(BaseModel):
    """Totalizadores gerais exibidos no topo do Painel Executivo."""

    total_projetos: int = Field(..., description="Quantidade total de projetos elegíveis")
    potencia_total_mw: Decimal = Field(..., description="Soma da potência outorgada, em MW")
    total_clientes: int = Field(..., description="Quantidade de clientes distintos com projetos")
    projetos_pendentes_revisao: int = Field(
        ..., description="Projetos elegíveis cujo status_revisao ainda está pendente "
                          "(informativo — NÃO são excluídos dos totais acima)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_projetos": 1523,
                "potencia_total_mw": "48210.75",
                "total_clientes": 87,
                "projetos_pendentes_revisao": 34,
            }
        }
    )


class PotenciaPorUFItem(BaseModel):
    """Um ponto do gráfico de Potência por UF."""

    uf: str = Field(..., description="Sigla da Unidade Federativa (ex: 'SP', 'CE')")
    potencia_total: Decimal = Field(..., description="Soma da potência outorgada na UF, em MW")
    total_projetos: int = Field(..., description="Quantidade de projetos elegíveis na UF")


class PotenciaPorUFResponse(BaseModel):
    dados: List[PotenciaPorUFItem]


class EvolucaoAnualItem(BaseModel):
    """Um ponto do gráfico de Evolução Anual."""

    ano: int = Field(..., description="Ano de referência (ano de operação/outorga)")
    potencia_total: Decimal = Field(..., description="Soma da potência outorgada no ano, em MW")
    total_projetos: int = Field(..., description="Quantidade de projetos elegíveis no ano")
    potencia_acumulada: Decimal = Field(
        ..., description="Potência acumulada até o ano (soma corrida, para curva de evolução)"
    )


class EvolucaoAnualResponse(BaseModel):
    dados: List[EvolucaoAnualItem]