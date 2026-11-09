import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Link2 } from "lucide-react";
import { ModalVincularCliente } from "./ModalVincularCliente";

export function TabelaSemProprietario({ dados }: { dados: any[] }) {
  const [projetoSelecionado, setProjetoSelecionado] = useState<any | null>(null);

  if (!dados || dados.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
        Nenhum projeto sem proprietário encontrado com os filtros atuais.
      </div>
    );
  }

  return (
    <>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>CEG</TableHead>
              <TableHead>Nome do Projeto</TableHead>
              <TableHead>UF</TableHead>
              <TableHead>Fase</TableHead>
              <TableHead className="text-right">Potência (MW)</TableHead>
              <TableHead className="text-center">Ação</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {dados.map((projeto) => (
              <TableRow key={projeto.ceg}>
                <TableCell className="font-medium">{projeto.ceg}</TableCell>
                <TableCell>{projeto.nome_projeto}</TableCell>
                <TableCell>{projeto.uf || "-"}</TableCell>
                <TableCell>{projeto.fase}</TableCell>
                <TableCell className="text-right">
                  {projeto.potencia_mw.toLocaleString("pt-BR", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </TableCell>
                <TableCell className="text-center">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="h-8 gap-1"
                    onClick={() => setProjetoSelecionado(projeto)}
                  >
                    <Link2 className="h-4 w-4" />
                    <span>Vincular</span>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <ModalVincularCliente 
        isOpen={!!projetoSelecionado}
        onClose={() => setProjetoSelecionado(null)}
        projeto={projetoSelecionado}
      />
    </>
  );
}