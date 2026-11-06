import React, { useState, useEffect } from "react";
// Importando os nomes exatos que existem no seu arquivo
import { useFiltros, Filtros } from "@/lib/useFiltros"; 

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// Criando os auxiliares localmente já que seu arquivo useFiltros não os exporta
const VAZIOS: Filtros = { origem: "", cliente: "", nome: "", uf: "", municipio: "", ano: "" };

const countActive = (f: Filtros) => 
  Object.values(f).filter((val) => val !== "").length;

// Cores do texto da sidebar (fundo verde escuro): tudo em branco.
// O menu que abre ao clicar no Select (SelectContent) mantém as cores padrão do tema.
const LABEL_CLASS = "text-white";
const SELECT_TRIGGER_CLASS = "text-white data-[placeholder]:text-white/70";
const INPUT_CLASS = "text-white placeholder:text-white/60 disabled:text-white/50";

export function FiltersPanel() {
  // Pegando as funções e estados com os nomes exatos do seu hook
  const { filtros, setFiltros, limpar } = useFiltros();
  
  const [draft, setDraft] = useState<Filtros>(filtros);

  useEffect(() => {
    setDraft(filtros);
  }, [filtros]);

  const handleChange = (key: keyof Filtros, value: string) => {
    setDraft((prev: Filtros) => {
      const next = { ...prev, [key]: value };
      // Regra de negócio: trocar a UF zera o município
      if (key === "uf") {
        next.municipio = "";
      }
      return next;
    });
  };

  const handleApply = () => setFiltros(draft);
  
  const handleClear = () => {
    setDraft(VAZIOS);
    limpar(); 
  };

  const draftActiveCount = countActive(draft);

  return (
    <div className="flex flex-col gap-5 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Filtros</h3>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="origem" className={LABEL_CLASS}>Origem</Label>
        <Select 
          value={draft.origem || undefined} 
          onValueChange={(v: string) => handleChange("origem", v === "todas" ? "" : v)}
        >
          <SelectTrigger id="origem" className={SELECT_TRIGGER_CLASS}>
            <SelectValue placeholder="Todas" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todas">Todas</SelectItem>
            <SelectItem value="solar">Solar</SelectItem>
            <SelectItem value="eolica">Eólica</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="cliente" className={LABEL_CLASS}>Cliente</Label>
        <Select 
          value={draft.cliente || undefined} 
          onValueChange={(v: string) => handleChange("cliente", v === "todos" ? "" : v)}
        >
          <SelectTrigger id="cliente" className={SELECT_TRIGGER_CLASS}>
            <SelectValue placeholder="Todos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos</SelectItem>
            {/* Aqui você mapeará os clientes da API no futuro */}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="nome" className={LABEL_CLASS}>Nome do Projeto</Label>
        <Input 
          id="nome"
          type="text"
          className={INPUT_CLASS}
          value={draft.nome}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange("nome", e.target.value)}
          placeholder="Ex: UFV Primavera"
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="uf" className={LABEL_CLASS}>UF</Label>
        <Select 
          value={draft.uf || undefined} 
          onValueChange={(v: string) => handleChange("uf", v === "todas" ? "" : v)}
        >
          <SelectTrigger id="uf" className={SELECT_TRIGGER_CLASS}>
            <SelectValue placeholder="Todas" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todas">Todas</SelectItem>
            <SelectItem value="MG">Minas Gerais (MG)</SelectItem>
            <SelectItem value="BA">Bahia (BA)</SelectItem>
            <SelectItem value="CE">Ceará (CE)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="municipio" className={LABEL_CLASS}>Município</Label>
        <Input 
          id="municipio"
          type="text"
          className={INPUT_CLASS}
          value={draft.municipio}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange("municipio", e.target.value)}
          disabled={!draft.uf}
          placeholder={draft.uf ? "Ex: Belo Horizonte" : "Selecione a UF primeiro"}
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="ano" className={LABEL_CLASS}>Ano de Vigência</Label>
        <Input 
          id="ano"
          type="number"
          className={INPUT_CLASS}
          value={draft.ano}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange("ano", e.target.value)}
          placeholder="Ex: 2024"
        />
      </div>

      <div className="mt-4 flex flex-col gap-2">
        <Button onClick={handleApply} className="w-full bg-brand text-white hover:bg-brand/90">
          Aplicar Filtros {draftActiveCount > 0 && `(${draftActiveCount})`}
        </Button>
        <Button onClick={handleClear} variant="outline" className="w-full">
          Limpar Filtros
        </Button>
      </div>
    </div>
  );
}