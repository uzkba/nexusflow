import { useFiltros } from "@/lib/useFiltros";
import { ProjetosTable } from "@/components/projetos/ProjetosTable";

export function BaseDeDadosPage() {
  const { filtros } = useFiltros();
  
  // Limpa os filtros globais vazios para passar para a tabela
  const paramsAtivos = Object.fromEntries(
    Object.entries(filtros).filter(([_, valor]) => valor !== "" && valor != null)
  );

  return (
    <div className="flex-1 space-y-6 p-8">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Base de Dados de Projetos</h2>
      </div>

      <div className="rounded-xl border bg-card text-card-foreground shadow p-6">
        {/* A tabela recebe os filtros globais exatamente como fazia na Visão Geral */}
        <ProjetosTable filtrosGlobais={paramsAtivos} /> 
      </div>
    </div>
  );
}