import { Zap } from "lucide-react";
import { Sidebar, SidebarHeader, SidebarContent, SidebarRail } from "@/components/ui/sidebar";
import { FiltersPanel } from "./filters-panel";

export function AppSidebar() {
  return (
    // 'none' ou 'sidebar' fixo impede que ela vire drawer/offcanvas por cima da tela
    <Sidebar collapsible="none" className="border-r border-sidebar-border bg-sidebar text-sidebar-foreground h-screen sticky top-0">
      <SidebarHeader className="p-0 border-b border-sidebar-border/40">
        <div className="flex items-center gap-2.5 px-5 py-5">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-brand">
            <Zap className="h-4 w-4 text-white" />
          </div>
          <span className="font-bold tracking-wide text-white">ENERGIA</span>
        </div>
      </SidebarHeader>

      <SidebarContent className="p-0 overflow-y-auto">
        <FiltersPanel />
      </SidebarContent>
      
      <SidebarRail />
    </Sidebar>
  );
}