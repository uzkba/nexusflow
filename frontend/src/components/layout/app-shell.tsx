import type { CSSProperties } from "react";
import { Outlet } from "react-router-dom";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { usePersistedSidebar } from "@/hooks/use-persisted-sidebar";
import { AppHeader } from "./app-header";
import { AppSidebar } from "./app-sidebar";

export function AppShell() {
  const [open, setOpen] = usePersistedSidebar(true);

  return (
    <SidebarProvider
      open={open}
      onOpenChange={setOpen}
      style={{ "--sidebar-width": "15.5rem" } as CSSProperties}
    >
      <AppSidebar />
      <SidebarInset className="min-w-0 bg-surface">
        {/* TODO: updatedAt = data da última execução do ETL (tabela etl_runs) */}
        <AppHeader />
        <main className="flex-1 p-4 md:p-8">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}