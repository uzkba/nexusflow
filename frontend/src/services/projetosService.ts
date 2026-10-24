// frontend/src/services/projetosService.ts

import { httpClient } from '@/lib/httpClient'; 
import { PaginatedResponse, ProjetoOut, ProjetosQueryParams } from '@/types/projetos';

export async function getProjetos(params: ProjetosQueryParams): Promise<PaginatedResponse<ProjetoOut>> {
  // Limpa propriedades undefined/vazias para não enviar na query string
  const cleanParams = Object.fromEntries(
    Object.entries(params).filter(([_, v]) => v !== undefined && v !== '')
  );

  const { data } = await httpClient.get<PaginatedResponse<ProjetoOut>>('/api/projetos', {
    params: cleanParams,
  });
  
  return data;
}