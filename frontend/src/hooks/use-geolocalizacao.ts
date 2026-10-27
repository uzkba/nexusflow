// frontend/src/hooks/use-geolocalizacao.ts
import { useQuery } from '@tanstack/react-query';

// Contrato alinhado com o schema Pydantic do backend
export interface GeolocalizacaoItem {
  uf: string;
  municipio: string;
  quantidade_projetos: number;
  potencia_total: number;
}

export interface GeolocalizacaoResponse {
  total_municipios: number;
  dados: GeolocalizacaoItem[];
}

// Interface flexível para filtros globais
export interface FiltrosGeo {
  cliente_id?: string;
  status_revisao?: string;
  [key: string]: any; 
}

const fetchGeolocalizacao = async (filtros: FiltrosGeo): Promise<GeolocalizacaoResponse> => {
  const params = new URLSearchParams();
  
  Object.entries(filtros).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.append(key, String(value));
    }
  });

  const queryString = params.toString();
  
  // URL corrigida sem crases aninhadas problemáticas
  const url = queryString 
    ? `/api/geolocalizacao?${queryString}` 
    : '/api/geolocalizacao';

  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error('Erro ao buscar os dados de geolocalização');
  }
  
  return response.json();
};

export const useGeolocalizacao = (filtros: FiltrosGeo = {}) => {
  return useQuery({
    queryKey: ['geolocalizacao', filtros],
    queryFn: () => fetchGeolocalizacao(filtros),
    staleTime: 1000 * 60 * 5, // Cache de 5 minutos
  });
};