import { render, screen, fireEvent } from '@testing-library/react';
import { ProjetosTable } from '../projetos/ProjetosTable'; // Ajuste o caminho
import * as useProjetosHook from '@/hooks/use-projetos';
import { vi } from 'vitest';

// Mockamos o hook que faz a requisição
vi.mock('@/hooks/use-projetos');

describe('ProjetosTable Component', () => {
  const mockProjetos = {
    items: [
      {
        ceg: '12345',
        nome_projeto: 'Usina Solar Aurora',
        origem: 'Solar',
        uf: 'SP',
        potencia_outorgada_kw: 50000,
        status_revisao: 'aprovado'
      }
    ],
    total: 25, // Total de itens falsos
    pages: 3   // Total de páginas falsas
  };

  it('deve renderizar os dados mockados corretamente', () => {
    // Configuramos o mock para retornar os dados falsos e não estar em loading
    vi.spyOn(useProjetosHook, 'useProjetos').mockReturnValue({
      data: mockProjetos,
      isLoading: false,
      isError: false,
    } as any);

    render(<ProjetosTable />);

    // Verifica se os dados da Usina Aurora apareceram na tela
    expect(screen.getByText('Usina Solar Aurora')).toBeInTheDocument();
    expect(screen.getByText('Solar')).toBeInTheDocument();
    expect(screen.getByText('SP')).toBeInTheDocument();
    expect(screen.getByText('50.000')).toBeInTheDocument(); // Formatado com toLocaleString
    expect(screen.getByText('Aprovado')).toBeInTheDocument(); // Badge
  });

  it('deve interagir com a paginação e mudar a página atual', () => {
    // Um spy para monitorar com quais parâmetros o hook de dados é chamado
    const spyUseProjetos = vi.spyOn(useProjetosHook, 'useProjetos').mockReturnValue({
      data: mockProjetos,
      isLoading: false,
      isError: false,
    } as any);

    render(<ProjetosTable />);

    // Verifica que o texto inicial é "Página 1 de 3"
    expect(screen.getByText('Página 1 de 3')).toBeInTheDocument();

    // Acha o botão "Próxima" e clica nele
    const btnProxima = screen.getByRole('button', { name: /próxima/i });
    fireEvent.click(btnProxima);

    // Como o botão altera o estado local, o componente re-renderiza e chama useProjetos com page: 2
    expect(screen.getByText('Página 2 de 3')).toBeInTheDocument();
    
    // Verificamos se a nossa API (via hook) foi chamada pedindo a página 2
    expect(spyUseProjetos).toHaveBeenLastCalledWith(expect.objectContaining({
      page: 2
    }));
  });

  it('deve desabilitar o botão "Anterior" na primeira página', () => {
    vi.spyOn(useProjetosHook, 'useProjetos').mockReturnValue({
      data: mockProjetos,
      isLoading: false,
      isError: false,
    } as any);

    render(<ProjetosTable />);

    const btnAnterior = screen.getByRole('button', { name: /anterior/i });
    expect(btnAnterior).toBeDisabled();
  });
});