from typing import List
from pydantic import BaseModel, Field

class GeolocalizacaoItem(BaseModel):
    uf: str = Field(..., description="Sigla da Unidade Federativa (ex: SP, BA)")
    municipio: str = Field(..., description="Nome do município")
    quantidade_projetos: int = Field(..., description="Total de usinas/projetos cadastrados no município")
    potencia_total: float = Field(..., description="Soma da potência outorgada (kW) no município")
    latitude: float = Field(0.0, description="Latitude média para o mapa")
    longitude: float = Field(0.0, description="Longitude média para o mapa")

class GeolocalizacaoResponse(BaseModel):
    total_municipios: int = Field(..., description="Total de municípios únicos retornados")
    dados: List[GeolocalizacaoItem] = Field(
        ..., description="Lista de dados agregados por município para o mapa e tabela"
    )