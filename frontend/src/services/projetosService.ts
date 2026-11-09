import { httpClient } from '@/lib/httpClient'; 
import { PaginatedResponse, ProjetoOut, ProjetosQueryParams } from '@/types/projetos';

export async function getProjetos(params: ProjetosQueryParams): Promise<PaginatedResponse<ProjetoOut>> {
  const cleanParams = Object.fromEntries(
    Object.entries(params).filter(([_, v]) => v !== undefined && v !== '')
  );

  const { data } = await httpClient.get<PaginatedResponse<ProjetoOut>>('/api/projetos', {
    params: cleanParams,
  });
  
  return data;
}

// NOVA FUNÇÃO: Chama a nossa nova rota PATCH
export async function vincularCliente(ceg: string, clienteId: string): Promise<{ mensagem: string; ceg: string }> {
  const { data } = await httpClient.patch(`/api/${ceg}/vincular`, { 
    cliente_id: clienteId 
  });
  return data;
}