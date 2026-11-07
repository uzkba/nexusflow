import React, { useState, useEffect } from "react";
import { useFiltros, Filtros } from "@/lib/useFiltros"; 
import { useFilterOptions } from "@/hooks/use-filter-options"; 

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

const VAZIOS: Filtros = { origem: "", cliente: "", nome: "", uf: "", municipio: "", ano: "" };

const countActive = (f: Filtros) => 
  Object.values(f).filter((val) => val !== "").length;

export function FiltersPanel() {
  const { filtros, setFiltros, limpar } = useFiltros();
  
  const [draft, setDraft] = useState<Filtros>(filtros);

  const { ufs, origens } = useFilterOptions(draft.uf);

  useEffect(() => {
    setDraft(filtros);
  }, [filtros]);

  const handleChange = (key: keyof Filtros, value: string) => {
    setDraft((prev: Filtros) => {
      const next = { ...prev, [key]: value };
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
        {/* Alterado para text-white */}
        <h3 className="text-sm font-semibold text-white">Filtros</h3>
      </div>

      <div className="flex flex-col gap-2">
        {/* Adicionado className="text-white" em todas as Labels */}
        <Label htmlFor="origem" className="text-white">Origem</Label>
        <Select 
          value={draft.origem || undefined} 
          onValueChange={(v: string) => handleChange("origem", v === "todas" ? "" : v)}
        >
          <SelectTrigger id="origem">
            <SelectValue placeholder="Todas" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todas">Todas</SelectItem>
            {origens.map((origem) => (
              <SelectItem key={origem.value} value={origem.value}>
                {origem.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="cliente" className="text-white">Cliente</Label>
        <Input 
          id="cliente"
          type="text"
          value={draft.cliente}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange("cliente", e.target.value)}
          placeholder="Ex: Empresa de Energia SA"
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="nome" className="text-white">Nome do Projeto</Label>
        <Input 
          id="nome"
          type="text"
          value={draft.nome}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange("nome", e.target.value)}
          placeholder="Ex: UFV Primavera"
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="uf" className="text-white">UF</Label>
        <Select 
          value={draft.uf || undefined} 
          onValueChange={(v: string) => handleChange("uf", v === "todas" ? "" : v)}
        >
          <SelectTrigger id="uf">
            <SelectValue placeholder="Todas" />
          </SelectTrigger>
          <SelectContent className="max-h-64">
            <SelectItem value="todas">Todas</SelectItem>
            {ufs.map((estado) => (
              <SelectItem key={estado.value} value={estado.value}>
                {estado.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="municipio" className="text-white">Município</Label>
        <Input 
          id="municipio"
          type="text"
          value={draft.municipio}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange("municipio", e.target.value)}
          disabled={!draft.uf}
          placeholder={draft.uf ? "Ex: Belo Horizonte" : "Selecione a UF primeiro"}
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="ano" className="text-white">Ano de Vigência</Label>
        <Input 
          id="ano"
          type="number"
          value={draft.ano}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleChange("ano", e.target.value)}
          placeholder="Ex: 2024"
        />
      </div>

      <div className="mt-4 flex flex-col gap-2">
        <Button onClick={handleApply} className="w-full bg-brand text-white hover:bg-brand/90">