import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { SidebarContent, SidebarFooter, useSidebar } from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";
import {
  EMPTY_FILTERS, FILTER_KEYS, countActive, useFilters, type FilterKey, type Filters,
} from "@/hooks/use-filters";
import { useFilterOptions, type Option } from "@/hooks/use-filter-options";

const ALL = "__all__"; // Radix Select não aceita value=""

function Field({
  id, label, tag, value, options, onChange, disabled, placeholder = "Todos",
}: {
  id: FilterKey; label: string; tag?: string; value: string; options: Option[];
  onChange: (v: string) => void; disabled?: boolean; placeholder?: string;
}) {
  const active = value !== "";
  const selected = options.find((o) => o.value === value);

  return (
    <div className="space-y-2">
      <div className="flex h-4 items-center justify-between">
        <label
          htmlFor={id}
          className={cn(
            "font-mono text-[11px] font-semibold uppercase tracking-[0.14em]",
            active ? "text-emerald-300" : "text-white/45",
          )}
        >
          {label}
        </label>
        {active ? (
          <span className="rounded-full bg-emerald-400/15 px-2 py-0.5 font-mono text-[10px] font-semibold uppercase text-emerald-300">
            ativo
          </span>
        ) : tag ? (
          <span className="rounded border border-white/15 px-1.5 font-mono text-[10px] text-white/40">
            {tag}
          </span>
        ) : null}
      </div>

      <Select value={value || ALL} onValueChange={(v) => onChange(v === ALL ? "" : v)} disabled={disabled}>
        <SelectTrigger
          id={id}
          className={cn(
            "h-11 border-white/10 bg-white/5 text-[15px] text-white focus:ring-emerald-300/40 [&>svg]:text-white/50",
            active && "border-emerald-300/60 ring-1 ring-emerald-300/30",
          )}
        >
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>{placeholder}</SelectItem>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      {active && selected && (
        <p className="flex items-center gap-1.5 font-mono text-[11px] text-emerald-300/80">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          {selected.label}
        </p>
      )}
    </div>
  );
}

export function FiltersPanel() {
  const { filters: applied, apply, clear } = useFilters();
  const { isMobile, setOpenMobile } = useSidebar();

  // rascunho: só vira filtro de verdade ao clicar em "Aplicar Filtros"
  const [draft, setDraft] = useState<Filters>(applied);
  useEffect(() => {
    setDraft(applied);
  }, [applied]);

  const opts = useFilterOptions(draft.uf);
  const draftCount = countActive(draft);
  const dirty = FILTER_KEYS.some((k) => draft[k] !== applied[k]);

  const set = (key: FilterKey) => (value: string) =>
    setDraft((d) => ({ ...d, [key]: value, ...(key === "uf" ? { municipio: "" } : {}) }));

  const onApply = () => {
    apply(draft);
    if (isMobile) setOpenMobile(false);
  };
  const onClear = () => {
    setDraft(EMPTY_FILTERS);
    clear();
  };

  return (
    <>
      <div className="flex items-center justify-between border-y border-white/10 px-5 py-3">
        <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-white/45">
          Filtros avançados
        </span>
        {draftCount > 0 && (
          <span className="rounded-full bg-emerald-400/15 px-2.5 py-0.5 font-mono text-[11px] font-semibold text-emerald-300">
            {draftCount} {draftCount === 1 ? "ativo" : "ativos"}
          </span>
        )}
      </div>

      <SidebarContent className="gap-5 px-5 py-5">
        <Field id="origem" label="Origem" value={draft.origem} options={opts.origens} onChange={set("origem")} />
        <Field id="cliente" label="Cliente" value={draft.cliente} options={opts.clientes} onChange={set("cliente")} />
        <Field id="nome" label="Nome do projeto" value={draft.nome} options={opts.projetos} onChange={set("nome")} />
        <Field id="uf" label="Estado (UF)" value={draft.uf} options={opts.ufs} onChange={set("uf")} />
        <Field
          id="municipio" label="Município" value={draft.municipio} options={opts.municipios}
          onChange={set("municipio")} disabled={!draft.uf}
          placeholder={draft.uf ? "Todos" : "Selecione a UF"}
        />
        <Field id="ano" label="Ano de vigência" tag="opcional" value={draft.ano} options={opts.anos} onChange={set("ano")} />
      </SidebarContent>

      <SidebarFooter className="gap-2 border-t border-white/10 p-5">
        <Button
          onClick={onApply}
          disabled={!dirty}
          className="h-11 w-full bg-brand font-semibold text-white hover:bg-brand/90 disabled:opacity-50"
        >
          Aplicar Filtros
          {draftCount > 0 && (
            <span className="ml-2 grid h-5 min-w-5 place-items-center rounded-full bg-white/25 px-1 text-xs">
              {draftCount}
            </span>
          )}
        </Button>
        <Button
          variant="outline"
          onClick={onClear}
          className="h-10 w-full border-white/15 bg-transparent text-white/80 hover:bg-white/10 hover:text-white"
        >
          Limpar Filtros
        </Button>
      </SidebarFooter>
    </>
  );
}