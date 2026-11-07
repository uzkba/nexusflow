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

// Projeto listado no detalhe de um município (GET /api/geolocalizacao/projetos)
export interface ProjetoDoMunicipio {
  ceg: string;
  nome_projeto: string | null;
  origem: string | null;
  fase: string | null;
  potencia_outorgada_kw: number | null;
}

export interface ProjetosDoMunicipioResponse {
  municipio: string;
  total: number;
  dados: ProjetoDoMunicipio[];
}

// Filtros globais da sidebar: mesmos nomes do FiltrosQuery do backend
export interface FiltrosGeo {
  origem?: string;
  cliente?: string;
  nome?: string;
  uf?: string;
  municipio?: string;
  ano?: string;
  [key: string]: any;
}

const montarUrl = (base: string, filtros: FiltrosGeo): string => {
  const params = new URLSearchParams();

  Object.entries(filtros).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.append(key, String(value));
    }
  });

  const queryString = params.toString();
  return queryString ? `${base}?${queryString}` : base;
};

const fetchGeolocalizacao = async (filtros: FiltrosGeo): Promise<GeolocalizacaoResponse> => {
  const response = await fetch(montarUrl('/api/geolocalizacao', filtros));

  if (!response.ok) {
    throw new Error('Erro ao buscar os dados de geolocalização');
  }

  return response.json();
};

const fetchProjetosDoMunicipio = async (
  filtros: FiltrosGeo,
  uf: string,
  municipio: string,
): Promise<ProjetosDoMunicipioResponse> => {
  // Filtros da sidebar + o município (e UF) da linha clicada no ranking
  const response = await fetch(
    montarUrl('/api/geolocalizacao/projetos', { ...filtros, uf, municipio }),
  );

  if (!response.ok) {
    throw new Error('Erro ao buscar os projetos do município');
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

// Só é chamado quando a linha do município é expandida (o componente monta sob demanda).
// A chave começa com 'geolocalizacao', então aprovar/rejeitar também a invalida.
export const useProjetosDoMunicipio = (filtros: FiltrosGeo, uf: string, municipio: string) => {
  return useQuery({
    queryKey: ['geolocalizacao', 'projetos', filtros, uf, municipio],
    queryFn: () => fetchProjetosDoMunicipio(filtros, uf, municipio),
    staleTime: 1000 * 60 * 5,
  });
};