import { useFiltros } from "@/lib/useFiltros";
import { KpiCards } from "@/components/dashboard/KpiCards";
import { useOrigemDashboard, useRankingClientes, useProjetosSemProprietario } from "@/hooks/use-dashboard";
import { GraficoOrigem } from "@/components/dashboard/GraficoOrigem";
import { GraficoRanking } from "@/components/dashboard/GraficoRanking";
import { TabelaSemProprietario } from "@/components/dashboard/TabelaSemProprietario";

export function VisaoGeralPage() {
  const { filtros } = useFiltros();
  
  const paramsAtivos = Object.fromEntries(
    Object.entries(filtros).filter(([_, valor]) => valor !== "" && valor != null)
  );

  const { data: graficoOrigem, isLoading: isLoadingOrigem } = useOrigemDashboard(paramsAtivos);
  const { data: graficoRanking, isLoading: isLoadingRanking } = useRankingClientes(paramsAtivos, 10);
  const { data: projetosSemProprietario, isLoading: isLoadingProjetos } = useProjetosSemProprietario(paramsAtivos);

  return (
    <div className="flex-1 space-y-6 p-8">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Visão Geral</h2>
      </div>

      <div className="space-y-6">
        <KpiCards filtros={paramsAtivos} />

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
          <div className="col-span-4 rounded-xl border bg-card text-card-foreground shadow p-6 min-h-400px flex flex-col">
            <h3 className="font-semibold mb-4">Top 10 Clientes por Potência</h3>
            {isLoadingRanking ? (
              <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
                Carregando ranking...
              </div>
            ) : (
              <div className="flex-1 h-300px">
                <GraficoRanking dados={graficoRanking || []} />
              </div>
            )}
          </div>
          
          <div className="col-span-3 rounded-xl border bg-card text-card-foreground shadow p-6 min-h-400px flex flex-col">
            <h3 className="font-semibold mb-4">Matriz de Geração (Solar x Eólica)</h3>
            {isLoadingOrigem ? (
              <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
                Carregando matriz...
              </div>
            ) : (
              <div className="flex-1 h-300px">
                <GraficoOrigem dados={graficoOrigem || []} />
              </div>
            )}
          </div>
        </div>

        {/* Nova Secção: Radar de Vendas */}
        <div className="rounded-xl border bg-card text-card-foreground shadow p-6 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Radar de Vendas: Projetos Sem Proprietário</h3>
            <span className="text-sm text-muted-foreground">
              {projetosSemProprietario?.length || 0} oportunidades encontradas
            </span>
          </div>
          
          {isLoadingProjetos ? (
            <div className="flex-1 flex items-center justify-center h-32 text-sm text-muted-foreground">
              Carregando oportunidades...
            </div>
          ) : (
            <TabelaSemProprietario dados={projetosSemProprietario || []} />
          )}
        </div>
      </div>
    </div>
  );
}