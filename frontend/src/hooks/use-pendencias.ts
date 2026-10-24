import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Pendencia } from '../types/pendencias';
// Importe o httpClient exatamente de onde você o criou (ajuste o caminho se necessário)
import { httpClient } from '@/lib/httpClient'; // ou '@/services/api', dependendo do nome do seu arquivo

const fetchPendencias = async (): Promise<Pendencia[]> => {
  const response = await httpClient.get('/api/consolidacoes/pendentes');
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

export const usePendencias = () => {
  return useQuery({
    queryKey: ['consolidacoes-pendentes'],
    queryFn: fetchPendencias,
  });
};

export const useMutatePendencia = () => {
  const queryClient = useQueryClient();

  const aprovar = useMutation({
    mutationFn: aprovarPendenciaFn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consolidacoes-pendentes'] });
    },
  });

  const rejeitar = useMutation({
    mutationFn: rejeitarPendenciaFn,
    onSuccess: () => {
      // TECH DEBT: O backend não limpa o diff_pendente ao rejeitar
      queryClient.invalidateQueries({ queryKey: ['consolidacoes-pendentes'] });
    },
  });

  return { aprovar, rejeitar };
};