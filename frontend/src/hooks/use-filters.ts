import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

export const FILTER_KEYS = ["origem", "cliente", "nome", "uf", "municipio", "ano"] as const;
export type FilterKey = (typeof FILTER_KEYS)[number];
export type Filters = Record<FilterKey, string>;

export const EMPTY_FILTERS: Filters = {
  origem: "", cliente: "", nome: "", uf: "", municipio: "", ano: "",
};

export const countActive = (f: Filters) => FILTER_KEYS.filter((k) => f[k] !== "").length;

/**
 * Filtros APLICADOS, guardados na URL (?origem=solar&uf=MG).
 * Qualquer página lê com `const { filters } = useFilters()` e repassa à API.
 * "" = sem filtro.
 */
export function useFilters() {
  const [params, setParams] = useSearchParams();

  // assinatura estável: o objeto só muda quando um filtro realmente muda
  const sig = FILTER_KEYS.map((k) => params.get(k) ?? "").join("\u0000");
  const filters = useMemo(() => {
    const values = sig.split("\u0000");
    return Object.fromEntries(FILTER_KEYS.map((k, i) => [k, values[i]])) as Filters;
  }, [sig]);

  const apply = useCallback(
    (next: Filters) => {
      setParams(
        (prev) => {
          const p = new URLSearchParams(prev);
          FILTER_KEYS.forEach((k) => (next[k] ? p.set(k, next[k]) : p.delete(k)));
          return p;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  const clear = useCallback(() => apply(EMPTY_FILTERS), [apply]);

  return { filters, apply, clear, activeCount: countActive(filters) };
}