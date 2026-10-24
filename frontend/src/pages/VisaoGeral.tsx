import { useEffect, useState } from "react";
// AJUSTE: Importando com o nome exato do seu arquivo e hook
import { useFiltros } from "@/lib/useFiltros";
import { httpClient } from "@/lib/httpClient";

// Tipagens básicas para o TypeScript não reclamar
interface KPIs {
  total_projetos: number;
  potencia_total_mw: number;
  total_clientes: number;
  projetos_pendentes_revisao: number;
}

export function VisaoGeralPage() {
  // Alterado para usar o hook e a variável em português
  const { filtros } = useFiltros();
  
  // Estados para guardar os dados da API
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [graficoUf, setGraficoUf] = useState<any[]>([]);
  const [graficoAno, setGraficoAno] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const carregarDados = async () => {
      setIsLoading(true);
      
      try {
        // 1. Limpa os filtros: lê de "filtros" e remove strings vazias
        const paramsAtivos = Object.fromEntries(
          Object.entries(filtros).filter(([_, valor]) => valor !== "")
        );

        // 2. Faz as 3 chamadas em paralelo para não travar a tela
        const [respKpis, respUf, respAno] = await Promise.all([
          httpClient.get("/api/kpis", { params: paramsAtivos }),
          httpClient.get("/api/graficos/potencia-uf", { params: paramsAtivos }),
          httpClient.get("/api/graficos/evolucao-anual", { params: paramsAtivos })
        ]);

        // 3. Salva no estado (os gráficos vêm dentro da chave "dados")
        setKpis(respKpis.data);
        setGraficoUf(respUf.data.dados);
        setGraficoAno(respAno.data.dados);
        
      } catch (error) {
        console.error("Erro ao buscar dados do dashboard:", error);
      } finally {
        setIsLoading(false);
      }
    };

    carregarDados();
  }, [filtros]); // Refaz a busca sempre que a variável "filtros" mudar

  return (
    <div className="flex-1 space-y-6 p-8">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Visão Geral</h2>
      </div>

      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <p className="text-sm text-muted-foreground">Carregando dados...</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* CARDS DE KPI */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border bg-card text-card-foreground shadow p-6">
              <p className="text-sm font-medium">Total de Projetos</p>
              <h3 className="text-2xl font-bold">{kpis?.total_projetos || 0}</h3>
            </div>
            <div className="rounded-xl border bg-card text-card-foreground shadow p-6">
              <p className="text-sm font-medium">Potência Total (MW)</p>
              <h3 className="text-2xl font-bold">{kpis?.potencia_total_mw?.toFixed(2) || "0.00"}</h3>
            </div>
            <div className="rounded-xl border bg-card text-card-foreground shadow p-6">
              <p className="text-sm font-medium">Clientes Ativos</p>
              <h3 className="text-2xl font-bold">{kpis?.total_clientes || 0}</h3>
            </div>
            <div className="rounded-xl border bg-card text-card-foreground shadow p-6">
              <p className="text-sm font-medium text-orange-600">Revisões Pendentes</p>
              <h3 className="text-2xl font-bold text-orange-600">{kpis?.projetos_pendentes_revisao || 0}</h3>
            </div>
          </div>

          {/* ÁREA DOS GRÁFICOS */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
            <div className="col-span-4 rounded-xl border bg-card text-card-foreground shadow p-6 h-96">
              <h3 className="font-semibold mb-4">Evolução Anual</h3>
              {/* AJUSTE: Insira seu componente echarts-for-react aqui usando a prop graficoAno */}
              <pre className="text-xs overflow-auto h-64">{JSON.stringify(graficoAno, null, 2)}</pre>
            </div>
            
            <div className="col-span-3 rounded-xl border bg-card text-card-foreground shadow p-6 h-96">
              <h3 className="font-semibold mb-4">Potência por UF</h3>
              {/* AJUSTE: Insira seu componente echarts-for-react aqui usando a prop graficoUf */}
              <pre className="text-xs overflow-auto h-64">{JSON.stringify(graficoUf, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}