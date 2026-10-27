// frontend/src/pages/PaginaGeolocalizacao.tsx
import React, { useState } from 'react';
import { useGeolocalizacao, FiltrosGeo } from '../hooks/use-geolocalizacao';
import { MapaGeo } from '../components/geolocalizacao/MapaGeo';
import { Loader2, AlertCircle } from 'lucide-react';

export const PaginaGeolocalizacao: React.FC = () => {
  const [filtros] = useState<FiltrosGeo>({});
  
  const { data, isLoading, isError, refetch } = useGeolocalizacao(filtros);

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
            Municípios com maior volume de projetos
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
                {data?.dados?.map((item, index) => (
                  <tr 
                    key={`${item.municipio}-${item.uf}`} 
                    className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted"
                  >
                    <td className="p-4 align-middle">
                      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                        {index + 1}
                      </span>
                    </td>
                    <td className="p-4 align-middle font-medium">{item.municipio}</td>
                    <td className="p-4 align-middle text-muted-foreground">{item.uf}</td>
                    <td className="p-4 align-middle text-right font-bold">{item.quantidade_projetos}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
      
    </div>
  );
};