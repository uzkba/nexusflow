import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutos de cache
      refetchOnWindowFocus: false, // Evita requisições extras ao trocar de aba
      retry: (failureCount, error: any) => {
        const status = error?.response?.status || error?.status;
        
        // Falhas por erro do cliente (4xx) não devem sofrer retry
        if (status >= 400 && status < 500) {
          return false;
        }
        
        // Quedas de rede (sem status) ou erros no servidor (5xx): tenta 1 vez
        return failureCount < 1;
      },
    },
  },
});