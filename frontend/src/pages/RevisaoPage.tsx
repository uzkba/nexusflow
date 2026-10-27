import { PainelPendencias } from "@/components/PainelPendencias";

export default function RevisaoPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      {/* Aqui você pode ter sua Sidebar ou Header do layout executivo */}
      <main>
        <PainelPendencias />
      </main>
    </div>
  );
}