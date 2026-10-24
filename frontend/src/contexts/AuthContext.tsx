import { createContext, useContext, useState, ReactNode } from "react";

interface Usuario {
  id: string;
  email: string;
  papel: string;
}

interface AuthContextData {
  usuario: Usuario | null;
  login: (respostaLogin: any) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextData>({} as AuthContextData);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(() => {
    // Tenta recuperar o usuário salvo ao iniciar a aplicação
    const usuarioSalvo = localStorage.getItem("usuario");
    return usuarioSalvo ? JSON.parse(usuarioSalvo) : null;
  });

  const login = (respostaLogin: any) => {
    // Extrai o token e o usuário da resposta da API
    const { access_token, user } = respostaLogin;
    
    if (access_token) {
      localStorage.setItem("token", access_token);
    }
    
    if (user) {
      localStorage.setItem("usuario", JSON.stringify(user));
      setUsuario(user);
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("usuario");
    setUsuario(null);
  };

  return (
    <AuthContext.Provider value={{ usuario, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);