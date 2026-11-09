import { httpClient } from "../lib/httpClient";

export const dashboardService = {
  getKPIs: async (filtros?: any) => {
    const response = await httpClient.get("/api/kpis", { params: filtros });
    return response.data;
  },

  // Matriz de Geração (Solar x Eólica): potência por origem
  getOrigem: async (filtros?: any) => {
    const response = await httpClient.get("/api/graficos/origem", { params: filtros });

    return response.data.dados.map((item: any) => ({
      origem: item.origem ?? "N/A",
      potencia_total_mw: Number(item.potencia_total_mw) || 0,
      total_projetos: item.total_projetos ?? 0,
    }));
  },

  // Top clientes por potência (apenas clientes reais, sem o sentinela)
  getRanking: async (filtros?: any, limite: number = 10) => {
    const response = await httpClient.get("/api/graficos/ranking-clientes", {
      params: { ...filtros, limite },
    });

    return response.data.dados.map((item: any) => ({
      cliente_id: item.cliente_id,
      nome_oficial: item.nome_oficial ?? "N/A",
      potencia_total_mw: Number(item.potencia_total_mw) || 0,
      total_projetos: item.total_projetos ?? 0,
    }));
  },

  // Obras sem proprietário para o radar de prospecção
  getProjetosSemProprietario: async (filtros?: any) => {
    const response = await httpClient.get("/api/projetos/sem-proprietario", { params: filtros });
    return response.data.dados;
  },
};