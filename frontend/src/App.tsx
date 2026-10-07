import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppShell } from "@/components/layout/app-shell";
import { Login } from "./pages/LoginPage";

// Só vale em desenvolvimento e só com VITE_BYPASS_AUTH=true no .env
const BYPASS_AUTH = import.meta.env.DEV && import.meta.env.VITE_BYPASS_AUTH === "true";

// Telas provisórias: substitua cada uma pela página real quando ficar pronta
const Placeholder = ({ title }: { title: string }) => (
  <div className="rounded-xl bg-white p-6 shadow-sm">
    <h2 className="text-lg font-semibold">{title}</h2>
  </div>
);

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />

          {/* ProtectedRoute (Outlet) > AppShell (Outlet) > página */}
          <Route element={BYPASS_AUTH ? <Outlet /> : <ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<Placeholder title="Visão Geral" />} />
              <Route path="/geolocalizacao" element={<Placeholder title="Geolocalização" />} />
              <Route path="/base-de-dados" element={<Placeholder title="Base de Dados" />} />
              <Route
                path="/aprovacao-consolidacao"
                element={<Placeholder title="Aprovação de Consolidação" />}
              />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}