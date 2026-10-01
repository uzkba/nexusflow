import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { httpClient } from "@/lib/httpClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

export function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErro(null);

    if (!email || !senha) {
      setErro("Por favor, preencha e-mail e senha.");
      return;
    }

    try {
      setCarregando(true);
      
      const { data } = await httpClient.post("/api/auth/login", { email, senha });
      login(data);
      navigate("/dashboard"); 
      
    } catch (error: any) {
      if (error.response) {
        if (error.response.status === 401) {
          setErro("E-mail ou senha incorretos.");
        } else {
          setErro(error.response.data?.detail || "Erro ao tentar fazer login.");
        }
      } else if (error.request) {
        setErro("Não foi possível conectar ao servidor. Tente novamente mais tarde.");
      } else {
        setErro("Ocorreu um erro inesperado.");
      }
    } finally {
      setCarregando(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl font-bold text-center">Entrar</CardTitle>
          <CardDescription className="text-center">
            Digite suas credenciais para acessar o sistema
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleLogin}>
          <CardContent className="space-y-4">
            {erro && (
              <div className="flex items-center gap-2 p-3 text-sm text-red-600 bg-red-50 rounded-md">
                <AlertCircle className="w-4 h-4" />
                <span>{erro}</span>
              </div>
            )}
            
            <div className="space-y-2">
              <Label htmlFor="email">E-mail</Label>
              <Input 
                id="email" 
                type="email" 
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={carregando}
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="senha">Senha</Label>
              <Input 
                id="senha" 
                type="password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                disabled={carregando}
                required
              />
            </div>
          </CardContent>
          <CardFooter>
            <Button type="submit" className="w-full" disabled={carregando}>
              {carregando ? "Entrando..." : "Entrar"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}

export default Login;