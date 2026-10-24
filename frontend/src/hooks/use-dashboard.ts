import { useQuery } from "@tanstack/react-query";
import { dashboardService } from "../services/dashboardService";
import type { DashboardFiltros } from "../types/dashboard";

// Chave base para facilitar a invalidação do cache globalmente, se necessário
export const DASHBOARD_KEYS = {
  all: ["dashboard"] as const,
  kpis: (filtros: DashboardFiltros) => [...DASHBOARD_KEYS.all, "kpis", filtros] as const,
  origem: (filtros: DashboardFiltros) => [...DASHBOARD_KEYS.all, "origem", filtros] as const,
  ranking: (filtros: DashboardFiltros, limite: number) => [...DASHBOARD_KEYS.all, "ranking", filtros, limite] as const,
};

export function useKPIs(filtros: DashboardFiltros = {}) {
  return useQuery({
    queryKey: DASHBOARD_KEYS.kpis(filtros),
    queryFn: () => dashboardService.getKPIs(filtros),
  });
}

export function useOrigemDashboard(filtros: DashboardFiltros = {}) {
  return useQuery({
    queryKey: DASHBOARD_KEYS.origem(filtros),
    queryFn: () => dashboardService.getOrigem(filtros),
  });
}

export function useRankingClientes(filtros: DashboardFiltros = {}, limite: number = 20) {
  return useQuery({
    queryKey: DASHBOARD_KEYS.ranking(filtros, limite),
    queryFn: () => dashboardService.getRanking(filtros, limite),
  });
}