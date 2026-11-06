export interface DiffItem {
  valor_antigo: string | number | null;
  valor_novo: string | number | null;
}

export type StatusRevisao = 'pendente' | 'aprovada' | 'rejeitada';

export type MotivoPendencia = 'consolidacao_nome' | 'alteracao_dado';

// Contrato alinhado com ConsolidacaoPendenteOut (GET /api/consolidacoes/pendentes)
export interface Pendencia {
  id: number;
  motivo_pendencia?: MotivoPendencia | null;
  status?: string;

  // Consolidação de nome
  nome_bruto_id?: number | null;
  nome_bruto?: string | null;
  cliente_sugerido_id?: string | null;
  cliente_sugerido_nome?: string | null;
  nomes_sugeridos_para_cliente?: number;
  score_similaridade?: number | null;
  cegs_relacionados?: string[] | null;

  // Agregados dos projetos ligados à pendência
  ufs?: string[];
  municipios?: string[];
  total_projetos?: number;
  potencia_total_mw?: number;

  // Alteração de dado (o CEG só existe neste caso)
  ceg?: string | null;
  // Agora é um Record (Dicionário) em vez de Array
  diff_pendente?: Record<string, DiffItem> | null;

  tipo?: string; // legado; o tipo real vem de motivo_pendencia
  status_revisao?: StatusRevisao;
  criado_em?: string;
}