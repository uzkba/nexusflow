import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

export const FILTRO_KEYS = ["origem", "cliente", "nome", "uf", "municipio", "ano"] as const;
export type Filtros = Record<(typeof FILTRO_KEYS)[number], string>;

const VAZIOS = Object.fromEntries(FILTRO_KEYS.map((k) => [k, ""])) as Filtros;

/**
 * Estado global dos filtros da sidebar, sincronizado com a query string.
 * Fonte da verdade: a URL (useSearchParams). Nenhum componente guarda cópia.
 */
export function useFiltros() {
  const [params, setParams] = useSearchParams();

  // Só as chaves de filtro: mudar ?page= (ou outros params) não altera isso.
  const search = useMemo(() => {
    const p = new URLSearchParams();
    FILTRO_KEYS.forEach((k) => {
      const v = params.get(k);
      if (v) p.set(k, v);
    });
    return p.toString();
  }, [params]);

  const filtros = useMemo<Filtros>(() => {
    const p = new URLSearchParams(search);
    return Object.fromEntries(FILTRO_KEYS.map((k) => [k, p.get(k) ?? ""])) as Filtros;
  }, [search]);

  const setFiltros = useCallback(
    (next: Filtros) => {
      setParams(
        (prev) => {
          const p = new URLSearchParams(prev);
          FILTRO_KEYS.forEach((k) => {
            p.delete(k);
            if (next[k]) p.set(k, next[k]);
          });
          p.delete("page"); // mudou o filtro -> volta para a página 1
          return p;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  const limpar = useCallback(() => setFiltros(VAZIOS), [setFiltros]);

  return { filtros, search: search ? `?${search}` : "", setFiltros, limpar };
}