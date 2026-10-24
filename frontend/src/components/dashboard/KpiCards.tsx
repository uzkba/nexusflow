import { useKPIs } from "../../hooks/use-dashboard";
import type { DashboardFiltros } from "../../types/dashboard";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Skeleton } from "../ui/skeleton";
import { 
  Zap, 
  Files, 
  Building2, 
  AlertTriangle, 
  HelpCircle 
} from "lucide-react";

export function KpiCards({ filtros }: { filtros?: DashboardFiltros }) {
  const { data: kpis, isLoading, isError } = useKPIs(filtros);

  if (isError) {
    return (
      <div className="p-4 border border-red-200 bg-red-50 text-red-600 rounded-md">
        Falha ao carregar os indicadores principais.
      </div>
    );
  }

  if (isLoading || !kpis) {
    return (
      <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-4 rounded-full" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16 mb-1" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  // Fallbacks de segurança: se a API não enviar o campo ou ele vier null, assume 0.
  const potencia = Number(kpis.potencia_total_mw) || 0;
  const projetos = kpis.total_projetos || 0;
  const clientes = kpis.total_clientes || 0;
  const pendentes = kpis.projetos_pendentes_revisao || 0;
  const semProprietario = kpis.projetos_sem_proprietario || 0;

  return (
    <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-5">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Potência Total
          </CardTitle>
          <Zap className="h-4 w-4 text-emerald-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {potencia.toLocaleString("pt-BR", { 
              minimumFractionDigits: 1, 
              maximumFractionDigits: 1 
            })} <span className="text-sm font-normal text-muted-foreground">MW</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Projetos Ativos
          </CardTitle>
          <Files className="h-4 w-4 text-blue-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {projetos.toLocaleString("pt-BR")}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Clientes Únicos
          </CardTitle>
          <Building2 className="h-4 w-4 text-indigo-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {clientes.toLocaleString("pt-BR")}
          </div>
        </CardContent>
      </Card>

      <Card className={pendentes > 0 ? "border-amber-200 bg-amber-50/30" : ""}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Revisão Pendente
          </CardTitle>
          <AlertTriangle className={`h-4 w-4 ${pendentes > 0 ? "text-amber-500" : "text-muted-foreground"}`} />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {pendentes.toLocaleString("pt-BR")}
          </div>
        </CardContent>
      </Card>

      <Card className={semProprietario > 0 ? "border-red-200 bg-red-50/30" : ""}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Sem Proprietário
          </CardTitle>
          <HelpCircle className={`h-4 w-4 ${semProprietario > 0 ? "text-red-500" : "text-muted-foreground"}`} />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {semProprietario.toLocaleString("pt-BR")}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}