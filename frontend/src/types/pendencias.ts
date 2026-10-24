export interface DiffItem {
  valor_antigo: string | number | null;
  valor_novo: string | number | null;
}

export type StatusRevisao = 'pendente' | 'aprovada' | 'rejeitada';

export interface Pendencia {
  id: number;
  ceg: string;
  tipo?: string; // Opcional, pois vimos que o banco usa outras lógicas (ex: motivo_pendencia)
  status_revisao: StatusRevisao;
  // Agora é um Record (Dicionário) em vez de Array
  diff_pendente?: Record<string, DiffItem> | null;
  cegs_relacionados?: string[];
  score_similaridade?: number; 
  criado_em?: string;
}