import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronsUpDown } from "lucide-react";

import { cn } from "@/lib/utils";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { httpClient } from "@/lib/httpClient";
import { DASHBOARD_KEYS } from "@/hooks/use-dashboard"; // Ajuste o caminho se necessário

type Cliente = { id: string; nome_oficial: string };

interface ModalVincularClienteProps {
  isOpen: boolean;
  onClose: () => void;
  projeto: { ceg: string; nome_projeto: string } | null;
}

export function ModalVincularCliente({ isOpen, onClose, projeto }: ModalVincularClienteProps) {
  const [clienteId, setClienteId] = useState<string>("");
  const [openBox, setOpenBox] = useState(false); // Controla a abertura do dropdown de pesquisa
  const queryClient = useQueryClient();

  const { data: clientes, isLoading: isLoadingClientes } = useQuery<Cliente[]>({
    queryKey: ["clientes-dropdown"],
    queryFn: async () => {
      const { data } = await httpClient.get("/api/clientes");
      return data;
    },
    enabled: isOpen,
  });

  const mutation = useMutation({
    mutationFn: async (id: string) => {
      if (!projeto) return;
      await httpClient.patch(`/api/${projeto.ceg}/vincular`, { cliente_id: id });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DASHBOARD_KEYS.all });
      fecharModal();
    },
  });

  const handleVincular = () => {
    if (clienteId) mutation.mutate(clienteId);
  };

  const fecharModal = () => {
    setClienteId("");
    setOpenBox(false);
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={fecharModal}>
      <DialogContent className="sm:max-w-425px">
        <DialogHeader>
          <DialogTitle>Vincular Cliente ao Projeto</DialogTitle>
        </DialogHeader>
        
        <div className="py-4 space-y-4">
          <p className="text-sm text-muted-foreground">
            Selecione o cliente proprietário para a obra <strong>{projeto?.nome_projeto}</strong> ({projeto?.ceg}).
          </p>
          
          <Popover open={openBox} onOpenChange={setOpenBox}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={openBox}
                className="w-full justify-between font-normal"
                disabled={isLoadingClientes || mutation.isPending}
              >
                {clienteId
                  ? clientes?.find((c) => c.id === clienteId)?.nome_oficial
                  : "Pesquisar cliente..."}
                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            
            {/* PopoverContent com a mesma largura do botão */}
            <PopoverContent className="w-375px p-0">
              <Command>
                <CommandInput placeholder="Digite o nome do cliente..." />
                <CommandList>
                  <CommandEmpty>Nenhum cliente encontrado.</CommandEmpty>
                  <CommandGroup>
                    {clientes?.map((c) => (
                      <CommandItem
                        key={c.id}
                        value={c.nome_oficial}
                        onSelect={() => {
                          // Se clicar no mesmo, desmarca. Se clicar noutro, marca.
                          setClienteId(c.id === clienteId ? "" : c.id);
                          setOpenBox(false); // Fecha o dropdown após escolher
                        }}
                      >
                        <Check
                          className={cn(
                            "mr-2 h-4 w-4",
                            clienteId === c.id ? "opacity-100" : "opacity-0"
                          )}
                        />
                        {c.nome_oficial}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>

        </div>

        <DialogFooter>
          <Button variant="outline" onClick={fecharModal} disabled={mutation.isPending}>
            Cancelar
          </Button>
          <Button onClick={handleVincular} disabled={!clienteId || mutation.isPending}>
            {mutation.isPending ? "A vincular..." : "Confirmar Vínculo"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}