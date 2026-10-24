// frontend/src/types/projetos.ts

export type ReviewStatus = 'pendente' | 'aprovado' | 'rejeitado';

export interface ProjetoOut {
  ceg: string;
  nome_projeto?: string | null;
  cliente_id?: string | null;
  uf?: string | null;
  municipios?: string[] | null;
  origem?: string | null;
  fase?: string | null;
  potencia_outorgada_kw?: number | null;
  inicio_vigencia_ano?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  status_revisao: ReviewStatus;
  criado_em: string;
  atualizado_em: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ProjetosQueryParams {
  page: number;
  size: number;
  uf?: string;
  status?: string;
  origem?: string;
  search?: string;
  sort_by?: string;
  sort_desc?: boolean;
}