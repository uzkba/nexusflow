import { useMemo } from "react";

export type Option = { value: string; label: string };

const UFS = [
  "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA",
  "PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO",
];

/**
 * Opções dos selects de filtro.
 * Origem, UF e ano são estáticos. Cliente, nome do projeto e município
 * dependem da API: preencha os TODO abaixo (único arquivo a mexer).
 */
export function useFilterOptions(_uf: string) {
  return useMemo(() => {
    const anoAtual = new Date().getFullYear();
    return {
      origens: [
        { value: "solar", label: "Solar" },
        { value: "eolica", label: "Eólica" },
      ] as Option[],
      ufs: UFS.map((u) => ({ value: u, label: u })) as Option[],
      anos: Array.from({ length: 15 }, (_, i) => {
        const a = String(anoAtual + 5 - i);
        return { value: a, label: a };
      }) as Option[],

      // TODO: carregar da API (ex.: lista de clientes/distribuidoras)
      clientes: [] as Option[],
      // TODO: carregar da API (lista grande: considerar combobox com busca)
      projetos: [] as Option[],
      // TODO: carregar da API usando a UF selecionada (_uf)
      municipios: [] as Option[],
    };
  }, [_uf]);
}