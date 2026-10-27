import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppShell } from "@/components/layout/app-shell";
import { Login } from "./pages/LoginPage";
import { VisaoGeralPage } from "./pages/VisaoGeral";
import { BaseDeDadosPage } from "./pages/BaseDeDados";
// 1. Importe a nova página de Geolocalização (ajuste o caminho se o nome do arquivo for diferente)
import { PaginaGeolocalizacao } from "./pages/Geolocalizacao"; 

const BYPASS_AUTH = import.meta.env.DEV && import.meta.env.VITE_BYPASS_AUTH === "true";

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

          <Route element={BYPASS_AUTH ? <Outlet /> : <ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<VisaoGeralPage />} />
              
              {/* 2. Substitua o Placeholder pela PaginaGeolocalizacao */}
              <Route path="/geolocalizacao" element={<PaginaGeolocalizacao />} />
              
              <Route path="/base-de-dados" element={<BaseDeDadosPage />} />
              
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