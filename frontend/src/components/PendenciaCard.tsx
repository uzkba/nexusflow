import React from 'react';
import { Pendencia } from '../types/pendencias';
import { DiffViewer } from './DiffViewer';
import { useMutatePendencia } from '../hooks/use-pendencias';

interface PendenciaCardProps {
  pendencia: Pendencia;
  // 'pendente': fila de revisão (Aprovar/Rejeitar). 'decidida': histórico (Reabrir/Trocar decisão).
  modo?: 'pendente' | 'decidida';
}

const MAX_MUNICIPIOS_VISIVEIS = 4;

const formatarMW = (mw?: number) =>
  (mw ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 });

const formatarData = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '';

export const PendenciaCard: React.FC<PendenciaCardProps> = ({ pendencia, modo = 'pendente' }) => {
  const { aprovar, rejeitar, reabrir, inverter } = useMutatePendencia();

  // O tipo real vem de motivo_pendencia (a API não envia "tipo")
  const isAlteracao =
    pendencia.motivo_pendencia === 'alteracao_dado' || pendencia.tipo === 'alteracao_dado';
  const isConsolidacao = !isAlteracao;

  const isDecidida = modo === 'decidida';
  const foiAprovada = pendencia.status === 'aprovado';

  const isLoading =
    aprovar.isPending || rejeitar.isPending || reabrir.isPending || inverter.isPending;
  const falhouAoAlterar = reabrir.isError || inverter.isError;

  const ufs = pendencia.ufs ?? [];
  const municipios = pendencia.municipios ?? [];
  const municipiosVisiveis = municipios.slice(0, MAX_MUNICIPIOS_VISIVEIS);
  const municipiosOcultos = municipios.length - municipiosVisiveis.length;
  const cegs = pendencia.cegs_relacionados ?? [];
  const temScore = pendencia.score_similaridade !== null && pendencia.score_similaridade !== undefined;
  const nomesNoGrupo = pendencia.nomes_sugeridos_para_cliente ?? 0;

  const nome = pendencia.nome_bruto ?? 'Nome não informado';
  const clienteSugerido = pendencia.cliente_sugerido_nome ?? 'Cliente não identificado';

  const handleReabrir = () => {
    if (window.confirm(`Reabrir "${nome}"? Ela volta para a fila de pendentes e os projetos ficam sem cliente.`)) {
      reabrir.mutate(pendencia.id);
    }
  };

  const handleInverter = () => {
    const destino = foiAprovada ? 'REJEITADA' : 'APROVADA';
    if (window.confirm(`Trocar a decisão de "${nome}" para ${destino}?`)) {
      inverter.mutate(pendencia.id);
    }
  };

  // Etiqueta no topo do card
  let etiqueta = isAlteracao ? 'Alteração de Dados' : 'Consolidação';
  let etiquetaClasse = isAlteracao ? 'bg-purple-100 text-purple-800' : 'bg-amber-100 text-amber-800';
  if (isDecidida) {
    etiqueta = foiAprovada ? 'Aprovada' : 'Rejeitada';
    etiquetaClasse = foiAprovada ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';
  }

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
              nome
            )}
          </h3>
          <span className={`shrink-0 px-2.5 py-0.5 rounded-full text-xs font-semibold ${etiquetaClasse}`}>
            {etiqueta}
          </span>
        </div>
        
        {/* NOVA DATA ADICIONADA AQUI */}
        {pendencia.criado_em && (
          <p className="text-xs text-gray-500 mt-1">
            Atualização recebida do ETL em: <span className="font-medium text-gray-700">{formatarData(pendencia.criado_em)}</span>
          </p>
        )}

        {isDecidida && pendencia.decidido_em && (
          <p className="text-xs text-gray-500">Decidida em {formatarData(pendencia.decidido_em)}</p>
        )}
      </div>

      <div className="p-6 pt-0">
        {/* Fluxo de Consolidação de nome */}
        {isConsolidacao && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              {!isDecidida && (
                <>
                  Agrupar este nome sob o cliente:{' '}
                  <span className="font-semibold text-gray-900">{clienteSugerido}</span>
                </>
              )}
              {isDecidida && foiAprovada && (
                <>
                  Agrupado sob o cliente:{' '}
                  <span className="font-semibold text-gray-900">{clienteSugerido}</span>
                </>
              )}
              {isDecidida && !foiAprovada && (
                <>
                  Agrupamento com <span className="font-semibold text-gray-900">{clienteSugerido}</span>{' '}
                  recusado: o nome foi tratado como cliente isolado.
                </>
              )}
            </p>

            {!isDecidida && nomesNoGrupo > 1 && (
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

      {falhouAoAlterar && (
        <p className="px-6 pb-2 text-sm text-red-600">
          Não foi possível alterar a decisão. Atualize a página e tente novamente.
        </p>
      )}

      <div className="flex items-center p-6 pt-0 gap-3 border-t mt-4">
        {!isDecidida ? (
          <>
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
          </>
        ) : (
          <>
            <button
              onClick={handleReabrir}
              disabled={isLoading}
              className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:opacity-50 disabled:pointer-events-none border border-gray-300 bg-white hover:bg-gray-100 text-gray-700 h-10 px-4 py-2 mt-4"
            >
              {reabrir.isPending ? 'Reabrindo...' : 'Reabrir'}
            </button>
            <button
              onClick={handleInverter}
              disabled={isLoading}
              className={`inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:opacity-50 disabled:pointer-events-none h-10 px-4 py-2 mt-4 ${
                foiAprovada
                  ? 'border border-red-200 bg-transparent hover:bg-red-100 text-red-600'
                  : 'bg-green-600 text-white hover:bg-green-700'
              }`}
            >
              {inverter.isPending
                ? 'Trocando...'
                : foiAprovada
                  ? 'Trocar para Rejeitada'
                  : 'Trocar para Aprovada'}
            </button>
          </>
        )}
      </div>
    </div>
  );
};