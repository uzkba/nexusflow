import { httpClient } from "../lib/httpClient";

export const dashboardService = {
  getKPIs: async (filtros?: any) => {
    // Rota corrigida para bater exatamente com o seu FastAPI
    const response = await httpClient.get("/api/kpis", { params: filtros });
    return response.data;
  },

  getOrigem: async (filtros?: any) => {
    // Apontamos para a rota real de UF do seu back-end
    const response = await httpClient.get("/api/graficos/potencia-uf", { params: filtros });
    
    // Adaptamos a resposta para o ECharts ler os dados corretamente sem precisar reescrever o componente
    return response.data.dados.map((item: any) => ({
      origem: item.uf || item.estado || "N/A",
      potencia_total_mw: item.potencia_total_mw || item.potencia || 0
    }));
  },

  getRanking: async (filtros?: any, limite: number = 20) => {
    // Apontamos para a rota real de Evolução Anual do seu back-end
    const response = await httpClient.get("/api/graficos/evolucao-anual", { params: { ...filtros, limite } });
    
    // Adaptamos a chave "ano" do Python para "nome_oficial" que o gráfico de barras espera
    return response.data.dados.map((item: any) => ({
      nome_oficial: String(item.ano || item.data || "N/A"),
      potencia_total_mw: item.potencia_total_mw || item.potencia || 0
    }));
  }
};