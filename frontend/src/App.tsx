import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
// 1. Importações do TanStack Query
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppShell } from "@/components/layout/app-shell";
import { Login } from "./pages/LoginPage";
import { VisaoGeralPage } from "./pages/VisaoGeral";
import { BaseDeDadosPage } from "./pages/BaseDeDados";
import { PaginaGeolocalizacao } from "./pages/Geolocalizacao"; 
// 2. Importe o painel que criamos (ajuste o caminho de acordo com sua estrutura de pastas)
import { PainelPendencias } from "./components/PainelPendencias"; 

const BYPASS_AUTH = import.meta.env.DEV && import.meta.env.VITE_BYPASS_AUTH === "true";

// Instância global do QueryClient configurada fora do componente para não recriar a cada render
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false, // Evita requisições extras ao mudar de aba no navegador (opcional, mas recomendado)
    },
  },
});

export default function App() {
  return (
    // 3. Provider do React Query envolvendo a aplicação
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />

            <Route element={BYPASS_AUTH ? <Outlet /> : <ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route path="/dashboard" element={<VisaoGeralPage />} />
                
                <Route path="/geolocalizacao" element={<PaginaGeolocalizacao />} />
                
                <Route path="/base-de-dados" element={<BaseDeDadosPage />} />
                
                {/* 4. Rota do painel de revisão agora com o componente real */}
                <Route
                  path="/aprovacao-consolidacao"
                  element={<PainelPendencias />}
                />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}