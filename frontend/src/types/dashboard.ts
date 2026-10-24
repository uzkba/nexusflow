export interface DashboardFiltros {
  origem?: "UFV" | "EOL";
  cliente?: string; // UUID
  nome?: string;
  uf?: string;
  municipio?: string;
  ano?: number;
}

export interface KPIsDashboard {
  total_projetos: number;
  potencia_total_mw: number;
  total_clientes: number;
  projetos_pendentes_revisao: number;
  projetos_sem_proprietario: number;
}

export interface OrigemGrafico {
  origem: string;
  potencia_total_mw: number;
  total_projetos: number;
}

export interface RankingCliente {
  cliente_id: string; // UUID
  nome_oficial: string;
  potencia_total_mw: number;
  total_projetos: number;
}