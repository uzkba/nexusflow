import React from 'react';
import { Pendencia } from '../types/pendencias';
import { DiffViewer } from './DiffViewer';
import { useMutatePendencia } from '../hooks/use-pendencias';

interface PendenciaCardProps {
  pendencia: Pendencia;
}

const MAX_MUNICIPIOS_VISIVEIS = 4;

const formatarMW = (mw?: number) =>
  (mw ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 });

export const PendenciaCard: React.FC<PendenciaCardProps> = ({ pendencia }) => {
  const { aprovar, rejeitar } = useMutatePendencia();

  // O tipo real vem de motivo_pendencia (a API não envia "tipo")
  const isAlteracao =
    pendencia.motivo_pendencia === 'alteracao_dado' || pendencia.tipo === 'alteracao_dado';
  const isConsolidacao = !isAlteracao;

  const isLoading = aprovar.isPending || rejeitar.isPending;

  const ufs = pendencia.ufs ?? [];
  const municipios = pendencia.municipios ?? [];
  const municipiosVisiveis = municipios.slice(0, MAX_MUNICIPIOS_VISIVEIS);
  const municipiosOcultos = municipios.length - municipiosVisiveis.length;
  const cegs = pendencia.cegs_relacionados ?? [];
  const temScore = pendencia.score_similaridade !== null && pendencia.score_similaridade !== undefined;
  const nomesNoGrupo = pendencia.nomes_sugeridos_para_cliente ?? 0;

  return (
    <div className="rounded-lg border text-card-foreground shadow-sm bg-white mb-4">
      <div className="flex flex-col space-y-1.5 p-6 pb-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold leading-tight tracking-tight">
            {isAlteracao ? (
              <>
                Projeto CEG: <span className="text-blue-600">{pendencia.ceg}</span>
              </>
            ) : (
              pendencia.nome_bruto ?? 'Nome não informado'
            )}
          </h3>
          <span
            className={`shrink-0 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
              isAlteracao ? 'bg-purple-100 text-purple-800' : 'bg-amber-100 text-amber-800'
            }`}
          >
            {isAlteracao ? 'Alteração de Dados' : 'Consolidação'}
          </span>
        </div>
      </div>

      <div className="p-6 pt-0">
        {/* Fluxo de Consolidação de nome */}
        {isConsolidacao && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              Agrupar este nome sob o cliente:{' '}
              <span className="font-semibold text-gray-900">
                {pendencia.cliente_sugerido_nome ?? 'Cliente não identificado'}
              </span>
            </p>

            {nomesNoGrupo > 1 && (
              <p className="text-xs text-gray-500">
                {nomesNoGrupo} nomes estão sendo agrupados neste mesmo cliente.
              </p>
            )}

            <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
              <div>
                <dt className="text-xs text-gray-500">Projetos</dt>
                <dd className="font-semibold">{pendencia.total_projetos ?? 0}</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500">Potência</dt>
                <dd className="font-semibold">{formatarMW(pendencia.potencia_total_mw)} MW</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500">UFs</dt>
                <dd className="font-semibold">{ufs.length > 0 ? ufs.join(', ') : '—'}</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500">Municípios</dt>
                <dd className="font-semibold">
                  {municipiosVisiveis.length > 0 ? municipiosVisiveis.join(', ') : '—'}
                  {municipiosOcultos > 0 && (
                    <span className="font-normal text-gray-500"> +{municipiosOcultos}</span>
                  )}
                </dd>
              </div>
            </dl>

            {cegs.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {cegs.map((c) => (
                  <span key={c} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded border">
                    {c}
                  </span>
                ))}
              </div>
            )}

            {/* Só mostra o score quando ele existe (nulo não é 0%) */}
            {temScore && (
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Score de Similaridade (RapidFuzz):</span>
                <span className="text-sm font-bold text-blue-700 bg-blue-50 px-2 py-1 rounded">
                  {Number(pendencia.score_similaridade).toFixed(2)}%
                </span>
              </div>
            )}
          </div>
        )}

        {/* Fluxo de Alteração de Dado: depende da existência do diff_pendente com chaves */}
        {pendencia.diff_pendente && Object.keys(pendencia.diff_pendente).length > 0 && (
          <div className="space-y-2 mt-4">
            <p className="text-sm text-gray-600 mb-2">As seguintes divergências foram encontradas:</p>
            <DiffViewer diffs={pendencia.diff_pendente} />
          </div>
        )}
      </div>

      <div className="flex items-center p-6 pt-0 gap-3 border-t mt-4">
        <button
          onClick={() => aprovar.mutate(pendencia.id)}
          disabled={isLoading}
          className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:opacity-50 disabled:pointer-events-none bg-green-600 text-white hover:bg-green-700 h-10 px-4 py-2 mt-4"
        >
          {aprovar.isPending ? 'Aprovando...' : 'Aprovar'}
        </button>
        <button
          onClick={() => rejeitar.mutate(pendencia.id)}
          disabled={isLoading}
          className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:opacity-50 disabled:pointer-events-none border border-red-200 bg-transparent hover:bg-red-100 text-red-600 h-10 px-4 py-2 mt-4"
        >
          {rejeitar.isPending ? 'Rejeitando...' : 'Rejeitar'}
        </button>
      </div>
    </div>
  );
};