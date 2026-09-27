from typing import List

from pydantic import BaseModel, Field


class GeolocalizacaoItem(BaseModel):
    uf: str = Field(..., description="Sigla da Unidade Federativa (ex: SP, BA)")
    municipio: str = Field(..., description="Nome do município")
    quantidade_projetos: int = Field(
        ..., description="Total de usinas/projetos cadastrados no município"
    )
    potencia_total: float = Field(
        ..., description="Soma da potência outorgada (kW) no município"
    )


class GeolocalizacaoResponse(BaseModel):
    total_municipios: int = Field(
        ..., description="Número de municípios distintos retornados"
    )
    dados: List[GeolocalizacaoItem]