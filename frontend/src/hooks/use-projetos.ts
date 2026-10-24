// frontend/src/hooks/use-projetos.ts

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { getProjetos } from '@/services/projetosService';
import { ProjetosQueryParams } from '@/types/projetos';

export function useProjetos(params: ProjetosQueryParams) {
  return useQuery({
    queryKey: ['projetos', 'list', params],
    queryFn: () => getProjetos(params),
    placeholderData: keepPreviousData,
    staleTime: 1000 * 60 * 5,
  });
}