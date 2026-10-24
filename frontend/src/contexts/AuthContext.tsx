import { createContext, useContext, useState, ReactNode } from "react";
// AJUSTE: Importe do seu path correto
import { httpClient } from "@/lib/httpClient"; 

interface Usuario {
  id: string;
  email: string;
  papel: string;
}

interface AuthContextData {
  usuario: Usuario | null;
  login: (respostaLogin: { user: Usuario }) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextData>({} as AuthContextData);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(() => {
    const usuarioSalvo = localStorage.getItem("usuario");
    return usuarioSalvo ? JSON.parse(usuarioSalvo) : null;
  });

  const login = (respostaLogin: { user: Usuario }) => {
    const { user } = respostaLogin;
    
    if (user) {
      localStorage.setItem("usuario", JSON.stringify(user));
      setUsuario(user);
    }
  };

  const logout = async () => {
    try {
      // Bate na API para destruir os cookies e o refresh no banco
      await httpClient.post("/api/auth/logout");
    } catch (error) {
      console.error("Erro ao realizar logout:", error);
    } finally {
      // Limpa dados locais e força recarregamento pra limpar memória
      localStorage.removeItem("usuario");
      setUsuario(null);
      window.location.href = "/login";
    }
  };

  return (
    <AuthContext.Provider value={{ usuario, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);