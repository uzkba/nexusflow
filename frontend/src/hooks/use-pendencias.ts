import { useQuery, useMutation, useQueryClient, QueryClient } from '@tanstack/react-query';
import { Pendencia } from '../types/pendencias';
// Importe o httpClient exatamente de onde você o criou (ajuste o caminho se necessário)
import { httpClient } from '@/lib/httpClient'; // ou '@/services/api', dependendo do nome do seu arquivo

// Filtros da sidebar (mesmos nomes do FiltrosQuery do backend). "" = sem filtro.
export type FiltrosPendencias = Partial<
  Record<'origem' | 'cliente' | 'nome' | 'uf' | 'municipio' | 'ano', string>
>;

export type Decisao = 'aprovado' | 'rejeitado';

// Remove filtros vazios: o backend rejeita "" em uf/ano/cliente (422)
const limparFiltros = (filtros: FiltrosPendencias) =>
  Object.fromEntries(
    Object.entries(filtros).filter(([, valor]) => valor !== undefined && valor !== null && valor !== ''),
  );

const fetchPendencias = async (filtros: FiltrosPendencias): Promise<Pendencia[]> => {
  const response = await httpClient.get('/api/consolidacoes/pendentes', {
    params: limparFiltros(filtros),
  });
  return response.data;
};

const fetchDecididas = async (filtros: FiltrosPendencias, decisao?: Decisao): Promise<Pendencia[]> => {
  const response = await httpClient.get('/api/consolidacoes/decididas', {
    params: { ...limparFiltros(filtros), ...(decisao ? { decisao } : {}) },
  });
  return response.data;
};

const aprovarPendenciaFn = async (id: number) => {
  const response = await httpClient.patch(`/api/consolidacoes/${id}/aprovar`);
  return response.data;
};

const rejeitarPendenciaFn = async (id: number) => {
  const response = await httpClient.patch(`/api/consolidacoes/${id}/rejeitar`);
  return response.data;
};

const reabrirPendenciaFn = async (id: number) => {
  const response = await httpClient.patch(`/api/consolidacoes/${id}/reabrir`);
  return response.data;
};

const inverterDecisaoFn = async (id: number) => {
  const response = await httpClient.patch(`/api/consolidacoes/${id}/inverter`);
  return response.data;
};

export const usePendencias = (filtros: FiltrosPendencias = {}) => {
  return useQuery({
    queryKey: ['consolidacoes-pendentes', filtros],
    queryFn: () => fetchPendencias(filtros),
  });
};

export const useDecididas = (filtros: FiltrosPendencias = {}, decisao?: Decisao) => {
  return useQuery({
    queryKey: ['consolidacoes-decididas', filtros, decisao ?? 'todas'],
    queryFn: () => fetchDecididas(filtros, decisao),
  });
};

// Toda decisão muda cliente_id e status dos projetos: recarrega filas e painéis.
// As chaves são prefixos, então invalidam todas as variações de filtro.
const invalidarTudo = (queryClient: QueryClient) => {
  ['consolidacoes-pendentes', 'consolidacoes-decididas', 'dashboard', 'geolocalizacao', 'projetos'].forEach(
    (chave) => queryClient.invalidateQueries({ queryKey: [chave] }),
  );
};

export const useMutatePendencia = () => {
  const queryClient = useQueryClient();

  const aprovar = useMutation({
    mutationFn: aprovarPendenciaFn,
    onSuccess: () => invalidarTudo(queryClient),
  });

  const rejeitar = useMutation({
    mutationFn: rejeitarPendenciaFn,
    // TECH DEBT: O backend não limpa o diff_pendente ao rejeitar
    onSuccess: () => invalidarTudo(queryClient),
  });

  // Desfaz a decisão: volta para a fila de pendentes
  const reabrir = useMutation({
    mutationFn: reabrirPendenciaFn,
    onSuccess: () => invalidarTudo(queryClient),
  });

  // Troca a decisão: aprovada <-> rejeitada
  const inverter = useMutation({
    mutationFn: inverterDecisaoFn,
    onSuccess: () => invalidarTudo(queryClient),
  });

  return { aprovar, rejeitar, reabrir, inverter };
};