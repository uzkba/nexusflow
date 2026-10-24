import React from 'react';
import { usePendencias } from '../hooks/use-pendencias';
import { PendenciaCard } from './PendenciaCard';

export const PainelPendencias: React.FC = () => {
  const { data: pendencias, isLoading, isError } = usePendencias();

  if (isLoading) {
    return (
      <div className="flex justify-center p-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4 bg-red-50 text-red-600 rounded-md border border-red-200">
        Erro ao carregar as pendências. Verifique a conexão com o servidor.
      </div>
    );
  }

  if (!pendencias || pendencias.length === 0) {
    return (
      <div className="p-8 text-center bg-gray-50 border border-dashed rounded-lg text-gray-500">
        Nenhuma pendência na fila de revisão no momento.
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold tracking-tight text-gray-900">Revisão de Pendências</h2>
        <p className="text-gray-500">Avalie solicitações de consolidação e alterações de declarações.</p>
      </div>

      <div className="space-y-4">
        {pendencias.map((pendencia) => (
          <PendenciaCard key={pendencia.id} pendencia={pendencia} />
        ))}
      </div>
    </div>
  );
};