import { Zap } from "lucide-react";
import { Sidebar, SidebarHeader, SidebarRail } from "@/components/ui/sidebar";
import { FiltersPanel } from "./filters-panel";

export function AppSidebar() {
  return (
    // offcanvas: no desktop desliza para fora; no mobile vira drawer (Sheet)
    <Sidebar collapsible="offcanvas">
      <SidebarHeader className="p-0">
        <div className="flex items-center gap-2.5 px-5 py-5">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-brand">
            <Zap className="h-4 w-4 text-white" />
          </div>
          <span className="font-bold tracking-wide text-white">ENERGIA</span>
        </div>
      </SidebarHeader>

      <FiltersPanel />
      <SidebarRail />
    </Sidebar>
  );
}