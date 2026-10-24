import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppShell } from "@/components/layout/app-shell";
import { Login } from "./pages/LoginPage";
// 1. Importe a página que acabamos de criar
import { VisaoGeralPage } from "./pages/VisaoGeral";

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
              {/* 2. Substitua o Placeholder pelo componente real aqui */}
              <Route path="/dashboard" element={<VisaoGeralPage />} />
              
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