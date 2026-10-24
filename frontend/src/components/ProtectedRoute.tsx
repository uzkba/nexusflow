import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

export function ProtectedRoute() {
  const { usuario } = useAuth();

  if (!usuario) {
    // Usuário não está logado, joga para a tela de login
    return <Navigate to="/login" replace />;
  }

  // Usuário está logado, permite renderizar a rota solicitada
  return <Outlet />;
}