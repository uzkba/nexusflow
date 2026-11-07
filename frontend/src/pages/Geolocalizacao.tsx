// frontend/src/pages/PaginaGeolocalizacao.tsx
import React, { useState } from 'react';
import {
  useGeolocalizacao,
  useProjetosDoMunicipio,
  FiltrosGeo,
} from '../hooks/use-geolocalizacao';
import { useFilters } from '../hooks/use-filters';
import { MapaGeo } from '../components/geolocalizacao/MapaGeo';
import { Loader2, AlertCircle, ChevronRight, ChevronDown } from 'lucide-react';

const formatarKw = (kw?: number | null) =>
  kw === null || kw === undefined
    ? '—'
    : `${kw.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} kW`;

const classeOrigem = (origem?: string | null) => {
  if (origem === 'Solar') return 'bg-amber-100 text-amber-800';
  if (origem === 'Eólica') return 'bg-sky-100 text-sky-800';
  return 'bg-gray-100 text-gray-700';
};

// Painel que expande sob a linha do município e lista os projetos dele
const ProjetosDoMunicipio: React.FC<{ filtros: FiltrosGeo; uf: string; municipio: string }> = ({
  filtros,
  uf,
  municipio,
}) => {
  const { data, isLoading, isError, refetch } = useProjetosDoMunicipio(filtros, uf, municipio);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-6 py-4 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Carregando projetos...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-3 px-6 py-4 text-sm text-destructive">
        <AlertCircle className="h-4 w-4" />
        Não foi possível carregar os projetos deste município.
        <button onClick={() => refetch()} className="underline">
          Tentar novamente
        </button>
      </div>
    );
  }

  const projetos = data?.dados ?? [];

  if (projetos.length === 0) {
    return (
      <div className="px-6 py-4 text-sm text-muted-foreground">
        Nenhum projeto encontrado para este município com os filtros atuais.
      </div>
    );
  }

  return (
    <div className="px-6 py-4">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {projetos.length} {projetos.length === 1 ? 'projeto' : 'projetos'}
      </p>
      <ul className="grid gap-2 sm:grid-cols-2">
        {projetos.map((p) => (
          <li
            key={p.ceg}
            className="flex items-start justify-between gap-3 rounded-md border bg-card px-3 py-2"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium" title={p.nome_projeto ?? p.ceg}>
                {p.nome_projeto ?? 'Projeto sem nome'}
              </p>
              <p className="truncate text-xs text-muted-foreground">{p.ceg}</p>
            </div>
            <div className="flex shrink-0 flex-col items-end gap-1">
              {p.origem && (
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${classeOrigem(p.origem)}`}>
                  {p.origem}
                </span>
              )}
              <span className="text-xs text-muted-foreground">{formatarKw(p.potencia_outorgada_kw)}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export const PaginaGeolocalizacao: React.FC = () => {
  // Filtros APLICADOS da sidebar (guardados na URL). Mesma fonte usada pela Visão Geral.
  const { filters } = useFilters();

  const { data, isLoading, isError, refetch } = useGeolocalizacao(filters);

  // Município expandido no ranking (um por vez)
  const [expandido, setExpandido] = useState<string | null>(null);
  const alternar = (chave: string) => setExpandido((atual) => (atual === chave ? null : chave));

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-100px)] w-full flex-col items-center justify-center space-y-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-muted-foreground text-sm font-medium">A carregar dados geográficos...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-[calc(100vh-100px)] w-full flex-col items-center justify-center space-y-4">
        <AlertCircle className="h-10 w-10 text-destructive" />
        <p className="text-destructive font-semibold">Falha ao carregar os dados de geolocalização.</p>
        <button
          onClick={() => refetch()}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Tentar Novamente
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 w-full pb-8">

      {/* Container do Mapa - Topo (Largura Total) */}
      <section className="w-full rounded-xl border bg-card p-5 text-card-foreground shadow-sm">
        <div className="mb-4">
          <h2 className="text-lg font-semibold tracking-tight">Distribuição de Projetos</h2>
          <p className="text-sm text-muted-foreground">
            Visão geográfica do portfólio de geração
          </p>
        </div>
        <div className="w-full rounded-md border bg-muted/20">
          {/* Atualizado para passar "dados" em vez de "projetos" */}
          {data?.dados && <MapaGeo dados={data.dados} />}
        </div>
      </section>

      {/* Container do Ranking - Base (Formato Tabela) */}
      <section className="w-full rounded-xl border bg-card p-5 text-card-foreground shadow-sm">
        <div className="mb-4">
          <h2 className="text-lg font-semibold tracking-tight">Ranking de Municípios</h2>
          <p className="text-sm text-muted-foreground">
            Municípios com maior volume de projetos. Clique em um município para ver os projetos.
          </p>
        </div>

        <div className="w-full overflow-x-auto">
          {/* Atualizado para verificar a length de "dados" */}
          {data?.dados?.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
              Nenhum município listado.
            </div>
          ) : (
            <table className="w-full caption-bottom text-sm">
              <thead className="[&_tr]:border-b">
                <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                  <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground w-100px">Posição</th>
                  <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Município</th>
                  <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">UF</th>
                  <th className="h-12 px-4 text-right align-middle font-medium text-muted-foreground">Projetos</th>
                </tr>
              </thead>
              <tbody className="[&_tr:last-child]:border-0">
                {/* Atualizado para mapear sobre "dados" */}
                {data?.dados?.map((item, index) => {
                  const chave = `${item.municipio}-${item.uf}`;
                  const aberto = expandido === chave;

                  return (
                    <React.Fragment key={chave}>
                      {/* O clique na linha inteira alterna; o botão dentro dela dá acesso por teclado */}
                      <tr
                        onClick={() => alternar(chave)}
                        className="cursor-pointer border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted"
                        data-state={aberto ? 'selected' : undefined}
                      >
                        <td className="p-4 align-middle">
                          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                            {index + 1}
                          </span>
                        </td>
                        <td className="p-4 align-middle font-medium">
                          <button
                            type="button"
                            aria-expanded={aberto}
                            className="flex items-center gap-2 text-left"
                          >
                            {aberto ? (
                              <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
                            ) : (
                              <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                            )}
                            {item.municipio}
                          </button>
                        </td>
                        <td className="p-4 align-middle text-muted-foreground">{item.uf}</td>
                        <td className="p-4 align-middle text-right font-bold">{item.quantidade_projetos}</td>
                      </tr>

                      {aberto && (
                        <tr className="border-b bg-muted/30">
                          <td colSpan={4} className="p-0">
                            <ProjetosDoMunicipio filtros={filters} uf={item.uf} municipio={item.municipio} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>

    </div>
  );
};