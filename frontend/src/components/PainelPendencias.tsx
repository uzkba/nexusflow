import React, { useState } from 'react';
import { usePendencias, useDecididas, Decisao } from '../hooks/use-pendencias';
import { useFilters } from '../hooks/use-filters';
import { PendenciaCard } from './PendenciaCard';

type Visao = 'pendentes' | 'decididas';

const Carregando: React.FC = () => (
  <div className="flex justify-center p-12">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
  </div>
);

const Erro: React.FC = () => (
  <div className="p-4 bg-red-50 text-red-600 rounded-md border border-red-200">
    Erro ao carregar as pendências. Verifique a conexão com o servidor.
  </div>
);

const Vazio: React.FC<{ texto: string }> = ({ texto }) => (
  <div className="p-8 text-center bg-gray-50 border border-dashed rounded-lg text-gray-500">{texto}</div>
);

const ListaPendentes: React.FC = () => {
  // Filtros APLICADOS da sidebar (guardados na URL): mesma fonte das outras abas
  const { filters, activeCount } = useFilters();
  const { data: pendencias, isLoading, isError } = usePendencias(filters);

  if (isLoading) return <Carregando />;
  if (isError) return <Erro />;
  if (!pendencias || pendencias.length === 0) {
    return (
      <Vazio
        texto={
          activeCount > 0
            ? 'Nenhuma pendência encontrada com os filtros atuais.'
            : 'Nenhuma pendência na fila de revisão no momento.'
        }
      />
    );
  }

  return (
    <>
      <p className="mb-4 text-sm text-gray-500">
        {pendencias.length} {pendencias.length === 1 ? 'pendência' : 'pendências'}
        {activeCount > 0 ? ' (filtradas)' : ''}
      </p>
      <div className="space-y-4">
        {pendencias.map((pendencia) => (
          <PendenciaCard key={pendencia.id} pendencia={pendencia} modo="pendente" />
        ))}
      </div>
    </>
  );
};

const FILTROS_DECISAO: { valor: Decisao | undefined; rotulo: string }[] = [
  { valor: undefined, rotulo: 'Todas' },
  { valor: 'aprovado', rotulo: 'Aprovadas' },
  { valor: 'rejeitado', rotulo: 'Rejeitadas' },
];

const ListaDecididas: React.FC = () => {
  const { filters, activeCount } = useFilters();
  const [decisao, setDecisao] = useState<Decisao | undefined>(undefined);
  const { data: decididas, isLoading, isError } = useDecididas(filters, decisao);

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {FILTROS_DECISAO.map((f) => (
          <button
            key={f.rotulo}
            onClick={() => setDecisao(f.valor)}
            className={`rounded-full border px-3 py-1 text-sm transition-colors ${
              decisao === f.valor
                ? 'border-gray-900 bg-gray-900 text-white'
                : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-100'
            }`}
          >
            {f.rotulo}
          </button>
        ))}
        {decididas && (
          <span className="ml-2 text-sm text-gray-500">
            {decididas.length} {decididas.length === 1 ? 'decisão' : 'decisões'}
            {activeCount > 0 ? ' (filtradas)' : ''}
          </span>
        )}
      </div>

      {isLoading && <Carregando />}
      {isError && <Erro />}
      {!isLoading && !isError && (!decididas || decididas.length === 0) && (
        <Vazio
          texto={
            activeCount > 0 || decisao
              ? 'Nenhuma decisão encontrada com os filtros atuais.'
              : 'Nenhuma consolidação foi decidida ainda.'
          }
        />
      )}
      {!isLoading && !isError && decididas && decididas.length > 0 && (
        <div className="space-y-4">
          {decididas.map((pendencia) => (
            <PendenciaCard key={pendencia.id} pendencia={pendencia} modo="decidida" />
          ))}
        </div>
      )}
    </>
  );
};

export const PainelPendencias: React.FC = () => {
  const [visao, setVisao] = useState<Visao>('pendentes');

  return (
    <div className="max-w-4xl mx-auto py-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold tracking-tight text-gray-900">Revisão de Pendências</h2>
        <p className="text-gray-500">Avalie solicitações de consolidação e alterações de declarações.</p>
      </div>

      <div className="mb-6 flex gap-2 border-b">
        {(
          [
            { id: 'pendentes', rotulo: 'Pendentes' },
            { id: 'decididas', rotulo: 'Decididas (reabrir ou trocar decisão)' },
          ] as { id: Visao; rotulo: string }[]
        ).map((aba) => (
          <button
            key={aba.id}
            onClick={() => setVisao(aba.id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              visao === aba.id
                ? 'border-orange-600 text-gray-900'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {aba.rotulo}
          </button>
        ))}
      </div>

      {visao === 'pendentes' ? <ListaPendentes /> : <ListaDecididas />}
    </div>
  );
};