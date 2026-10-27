import React from 'react';
import { Pendencia } from '../types/pendencias';
import { DiffViewer } from './DiffViewer';
import { useMutatePendencia } from '../hooks/use-pendencias';

interface PendenciaCardProps {
  pendencia: Pendencia;
}

export const PendenciaCard: React.FC<PendenciaCardProps> = ({ pendencia }) => {
  const { aprovar, rejeitar } = useMutatePendencia();
  
  // Define o layout visual da tag baseado no tipo, mas não bloqueia a renderização do Diff
  const isAlteracao = pendencia.tipo === 'alteracao_dado';
  const isConsolidacao = pendencia.tipo === 'consolidacao' || (!isAlteracao && !pendencia.diff_pendente);

  const isLoading = aprovar.isPending || rejeitar.isPending;

  return (
    <div className="rounded-lg border bg--card text-card-foreground shadow-sm bg-white mb-4">
      <div className="flex flex-col space-y-1.5 p-6 pb-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold leading-none tracking-tight">
            Projeto CEG: <span className="text-blue-600">{pendencia.ceg}</span>
          </h3>
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
            isAlteracao ? 'bg-purple-100 text-purple-800' : 'bg-amber-100 text-amber-800'
          }`}>
            {isAlteracao ? 'Alteração de Dados' : 'Consolidação'}
          </span>
        </div>
      </div>

      <div className="p-6 pt-0">
        {/* Renderização Condicional: Fluxo de Consolidação */}
        {isConsolidacao && pendencia.cegs_relacionados && (
          <div className="space-y-2">
            <p className="text-sm text-gray-600">Projetos candidatos para consolidação identificados:</p>
            <div className="flex gap-2 mb-3">
              {pendencia.cegs_relacionados.map(c => (
                <span key={c} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded border">
                  {c}
                </span>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Score de Similaridade (RapidFuzz):</span>
              <span className="text-sm font-bold text-blue-700 bg-blue-50 px-2 py-1 rounded">
                {(pendencia.score_similaridade || 0).toFixed(2)}%
              </span>
            </div>
          </div>
        )}

        {/* Renderização Condicional: Fluxo de Alteração de Dado */}
        {/* Agora depende apenas da existência do objeto diff_pendente e se ele tem chaves */}
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