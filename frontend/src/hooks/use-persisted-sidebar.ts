import { useCallback, useState } from "react";

const KEY = "nexusflow:sidebar-open";

/** Estado aberto/fechado da sidebar (desktop), persistido em localStorage. */
export function usePersistedSidebar(defaultOpen = true) {
  const [open, setOpenState] = useState<boolean>(() => {
    try {
      const v = localStorage.getItem(KEY);
      return v === null ? defaultOpen : v === "true";
    } catch {
      return defaultOpen;
    }
  });

  const setOpen = useCallback((value: boolean) => {
    setOpenState(value);
    try {
      localStorage.setItem(KEY, String(value));
    } catch {
      /* localStorage indisponível: segue só em memória */
    }
  }, []);

  return [open, setOpen] as const;
}