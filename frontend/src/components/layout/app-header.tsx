import { NavLink, useLocation } from "react-router-dom";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";

const TABS = [
  { label: "Visão Geral", to: "/dashboard" },
  { label: "Geolocalização", to: "/geolocalizacao" },
  { label: "Base de Dados", to: "/base-de-dados" },
  { label: "Aprovação de Consolidação", to: "/aprovacao-consolidacao" },
];

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const formatDate = (d: Date) => `${d.getDate()} ${MESES[d.getMonth()]} ${d.getFullYear()}`;

export function AppHeader({ updatedAt }: { updatedAt?: Date }) {
  const { search } = useLocation(); // mantém os filtros ao trocar de aba

  return (
    <header className="sticky top-0 z-20 border-b bg-white">
      <div className="flex items-start justify-between gap-4 px-4 pt-5 md:px-8">
        <div className="flex items-start gap-3">
          <SidebarTrigger className="-ml-2 mt-1" aria-label="Mostrar/ocultar filtros" />
          <div>
            <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-brand">
              Painel Executivo
            </p>
            <h1 className="text-2xl font-bold tracking-tight text-forest">Portfólio de Geração</h1>
          </div>
        </div>

        {updatedAt && (
          <div className="hidden text-right sm:block">
            <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">atualizado em</p>
            <p className="font-mono text-sm text-forest">{formatDate(updatedAt)}</p>
          </div>
        )}
      </div>

      <nav aria-label="Seções" className="mt-4 flex gap-1 overflow-x-auto px-4 md:px-8">
        {TABS.map((t) => (
          <NavLink
            key={t.to}
            to={{ pathname: t.to, search }}
            className={({ isActive }) =>
              cn(
                "whitespace-nowrap rounded-t-md border-b-2 px-5 py-3 text-[15px] transition-colors",
                isActive
                  ? "border-brand bg-surface font-semibold text-forest"
                  : "border-transparent font-medium text-muted-foreground hover:text-forest",
              )
            }
          >
            {t.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}