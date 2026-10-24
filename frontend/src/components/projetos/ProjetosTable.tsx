// frontend/src/components/projetos/ProjetosTable.tsx

import { useState } from 'react';
import { useProjetos } from '@/hooks/use-projetos';
import { ProjetosQueryParams, ReviewStatus } from '@/types/projetos';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react';

const StatusRevisaoBadge = ({ status }: { status: ReviewStatus }) => {
  const badgeConfig: Record<ReviewStatus, { label: string; className: string }> = {
    pendente: { label: 'Pendente', className: 'bg-yellow-500 hover:bg-yellow-600 text-white' },
    aprovado: { label: 'Aprovado', className: 'bg-green-500 hover:bg-green-600 text-white' },
    rejeitado: { label: 'Rejeitado', className: 'bg-red-500 hover:bg-red-600 text-white' },
  };

  const config = badgeConfig[status] || badgeConfig.pendente;

  return <Badge className={config.className}>{config.label}</Badge>;
};

// 1. Interface para tipar as propriedades que a tabela recebe de fora
interface ProjetosTableProps {
  filtrosGlobais?: Partial<ProjetosQueryParams>;
}

// 2. Desestruturamos a prop filtrosGlobais com valor default vazio
export function ProjetosTable({ filtrosGlobais = {} }: ProjetosTableProps) {
  // Estado inicial dos parâmetros da tabela (paginação e ordenação locais)
  const [paramsLocais, setParamsLocais] = useState<ProjetosQueryParams>({
    page: 1,
    size: 10,
    sort_by: 'criado_em',
    sort_desc: true,
  });

  // 3. Mesclamos os parâmetros locais com os filtros globais (uf, origem, etc)
  const parametrosCompletos = { ...paramsLocais, ...filtrosGlobais };

  // 4. Passamos os parâmetros combinados para o hook
  const { data, isLoading, isError } = useProjetos(parametrosCompletos);

  const handleSort = (column: string) => {
    setParamsLocais((prev) => ({
      ...prev,
      sort_by: column,
      // Se clicou na mesma coluna, inverte a ordem; senão, começa crescente (false)
      sort_desc: prev.sort_by === column ? !prev.sort_desc : false,
      page: 1, // Volta pra primeira página ao reordenar
    }));
  };

  const renderSortIcon = (column: string) => {
    if (paramsLocais.sort_by !== column) return <ArrowUpDown className="ml-2 h-4 w-4" />;
    return paramsLocais.sort_desc ? <ArrowDown className="ml-2 h-4 w-4" /> : <ArrowUp className="ml-2 h-4 w-4" />;
  };

  if (isError) {
    return (
      <div className="flex h-64 items-center justify-center rounded-md border text-red-500">
        Erro ao carregar a base de dados de projetos.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>
                <Button variant="ghost" onClick={() => handleSort('nome_projeto')} className="-ml-4">
                  Nome do Projeto {renderSortIcon('nome_projeto')}
                </Button>
              </TableHead>
              <TableHead>
                <Button variant="ghost" onClick={() => handleSort('origem')} className="-ml-4">
                  Origem {renderSortIcon('origem')}
                </Button>
              </TableHead>
              <TableHead>UF</TableHead>
              <TableHead>
                <Button variant="ghost" onClick={() => handleSort('potencia_outorgada_kw')} className="-ml-4">
                  Potência (kW) {renderSortIcon('potencia_outorgada_kw')}
                </Button>
              </TableHead>
              <TableHead>
                <Button variant="ghost" onClick={() => handleSort('status_revisao')} className="-ml-4">
                  Status de Revisão {renderSortIcon('status_revisao')}
                </Button>
              </TableHead>
            </TableRow>
          </TableHeader>
          
          <TableBody>
            {isLoading ? (
              // Skeletons com sintaxe corrigida do Tailwind
              Array.from({ length: paramsLocais.size }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell><Skeleton className="h-4 w-200px" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-80px" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-40px" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-100px" /></TableCell>
                  <TableCell><Skeleton className="h-6 w-80px rounded-full" /></TableCell>
                </TableRow>
              ))
            ) : data?.items.length === 0 ? (
              // Empty state
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                  Nenhum projeto encontrado com os filtros atuais.
                </TableCell>
              </TableRow>
            ) : (
              // Dados reais
              data?.items.map((projeto) => (
                <TableRow key={projeto.ceg}>
                  <TableCell className="font-medium">{projeto.nome_projeto || '-'}</TableCell>
                  <TableCell>{projeto.origem || '-'}</TableCell>
                  <TableCell>{projeto.uf || '-'}</TableCell>
                  <TableCell>
                    {projeto.potencia_outorgada_kw 
                      ? projeto.potencia_outorgada_kw.toLocaleString('pt-BR') 
                      : '-'}
                  </TableCell>
                  <TableCell>
                    <StatusRevisaoBadge status={projeto.status_revisao} />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Paginação */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          Total de {data?.total || 0} projetos
        </span>
        
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setParamsLocais((prev) => ({ ...prev, page: prev.page - 1 }))}
            disabled={paramsLocais.page === 1 || isLoading}
          >
            <ChevronLeft className="mr-2 h-4 w-4" />
            Anterior
          </Button>
          <span className="text-sm font-medium">
            Página {paramsLocais.page} de {data?.pages || 1}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setParamsLocais((prev) => ({ ...prev, page: prev.page + 1 }))}
            disabled={paramsLocais.page >= (data?.pages || 1) || isLoading}
          >
            Próxima
            <ChevronRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}