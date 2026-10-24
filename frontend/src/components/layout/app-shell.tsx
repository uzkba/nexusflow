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
      style={{ "--sidebar-width": "16rem" } as CSSProperties}
    >
      <div className="flex min-h-screen w-full bg-surface">
        {/* Sidebar fixa que acompanha a altura da tela */}
        <AppSidebar />
        
        {/* Área da direita contendo o Header e as páginas */}
        <SidebarInset className="flex flex-col flex-1 min-w-0 bg-surface overflow-x-hidden">
          <AppHeader />
          <main className="flex-1 p-4 md:p-8">
            <Outlet />
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}