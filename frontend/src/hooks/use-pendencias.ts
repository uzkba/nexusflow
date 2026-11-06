import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Pendencia } from '../types/pendencias';
// Importe o httpClient exatamente de onde você o criou (ajuste o caminho se necessário)
import { httpClient } from '@/lib/httpClient'; // ou '@/services/api', dependendo do nome do seu arquivo

// Filtros da sidebar (mesmos nomes do FiltrosQuery do backend). "" = sem filtro.
export type FiltrosPendencias = Partial<
  Record<'origem' | 'cliente' | 'nome' | 'uf' | 'municipio' | 'ano', string>
>;

const fetchPendencias = async (filtros: FiltrosPendencias): Promise<Pendencia[]> => {
  // Remove filtros vazios: o backend rejeita "" em uf/ano/cliente (422)
  const params = Object.fromEntries(
    Object.entries(filtros).filter(([, valor]) => valor !== undefined && valor !== null && valor !== ''),
  );
  const response = await httpClient.get('/api/consolidacoes/pendentes', { params });
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

export const usePendencias = (filtros: FiltrosPendencias = {}) => {
  return useQuery({
    queryKey: ['consolidacoes-pendentes', filtros],
    queryFn: () => fetchPendencias(filtros),
  });
};

export const useMutatePendencia = () => {
  const queryClient = useQueryClient();

  // A chave ['consolidacoes-pendentes'] invalida todas as variações de filtro (prefixo)
  const aprovar = useMutation({
    mutationFn: aprovarPendenciaFn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consolidacoes-pendentes'] });
      // Aprovar muda cliente_id e status dos projetos: os painéis precisam recarregar
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['geolocalizacao'] });
    },
  });

  const rejeitar = useMutation({
    mutationFn: rejeitarPendenciaFn,
    onSuccess: () => {
      // TECH DEBT: O backend não limpa o diff_pendente ao rejeitar
      queryClient.invalidateQueries({ queryKey: ['consolidacoes-pendentes'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['geolocalizacao'] });
    },
  });

  return { aprovar, rejeitar };
};