import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppShell } from "@/components/layout/app-shell";
import { Login } from "./pages/LoginPage";
import { VisaoGeralPage } from "./pages/VisaoGeral";
// 1. Importe a nova página de Base de Dados
import { BaseDeDadosPage } from "./pages/BaseDeDados"; 

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
              
              <Route path="/geolocalizacao" element={<Placeholder title="Geolocalização" />} />
              
              {/* 2. Substitua o Placeholder pelo componente real */}
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