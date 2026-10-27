import { render, screen } from '@testing-library/react';
import { KpiCards } from '../dashboard/KpiCards'; // Ajuste o caminho se necessário
import * as dashboardHooks from '@/hooks/use-dashboard';
import { vi } from 'vitest';

// Mock do seu hook real
vi.mock('@/hooks/use-dashboard');

describe('KpiCards', () => {
  it('deve exibir o layout de carregamento (skeletons) enquanto os dados estão carregando', () => {
    // Simulamos o estado de loading
    vi.spyOn(dashboardHooks, 'useKPIs').mockReturnValue({ 
      isLoading: true, 
      isError: false,
      data: null 
    } as any);
    
    render(<KpiCards />);
    
    // Como os skeletons do shadcn não têm texto, a melhor forma de testar o estado
    // de carregamento é garantir que os textos REAIS dos cards não estão na tela.
    expect(screen.queryByText('Potência Total')).not.toBeInTheDocument();
    expect(screen.queryByText('Projetos Ativos')).not.toBeInTheDocument();
  });

  it('deve exibir mensagem de erro caso a API falhe', () => {
    // Simulamos um erro no hook
    vi.spyOn(dashboardHooks, 'useKPIs').mockReturnValue({ 
      isLoading: false, 
      isError: true,
      data: null 
    } as any);
    
    render(<KpiCards />);
    
    // Verifica a mensagem exata do seu if (isError)
    expect(screen.getByText('Falha ao carregar os indicadores principais.')).toBeInTheDocument();
  });

  it('deve formatar e exibir os números corretamente após o fetch', () => {
    // Simulamos o sucesso injetando as chaves exatas do seu type
    vi.spyOn(dashboardHooks, 'useKPIs').mockReturnValue({
      isLoading: false,
      isError: false,
      data: { 
        potencia_total_mw: 1500.5, 
        total_projetos: 42,
        total_clientes: 10,
        projetos_pendentes_revisao: 3,
        projetos_sem_proprietario: 0 // Testa a classe condicional indiretamente
      } 
    } as any);
    
    render(<KpiCards />);
    
    // Garante que os cards renderizaram
    expect(screen.getByText('Potência Total')).toBeInTheDocument();
    
    // O valor 1500.5 em pt-BR com 1 casa decimal fica "1.500,5"
    // Como o "MW" está em um span separado, buscamos apenas pelo número.
    // Usamos expressão regular (/) para encontrar o texto flexível.
    expect(screen.getByText(/1\.500,5/)).toBeInTheDocument();
    expect(screen.getByText('MW')).toBeInTheDocument(); // O span separado
    
    // Verifica os outros indicadores exatos
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
  });
});