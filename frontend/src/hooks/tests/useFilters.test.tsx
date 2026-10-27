import { renderHook, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { useFilters, EMPTY_FILTERS } from '../use-filters'; // Ajuste o caminho se o hook tiver outro nome

describe('useFilters Hook', () => {
  // Wrapper necessário pois o hook usa useSearchParams do react-router-dom
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter initialEntries={['/']}>
      {children}
    </MemoryRouter>
  );

  it('deve inicializar com os filtros vazios (EMPTY_FILTERS)', () => {
    const { result } = renderHook(() => useFilters(), { wrapper });

    expect(result.current.filters).toEqual(EMPTY_FILTERS);
    expect(result.current.activeCount).toBe(0);
  });

  it('deve atualizar o estado ao aplicar um novo filtro', () => {
    const { result } = renderHook(() => useFilters(), { wrapper });

    act(() => {
      // Simula o usuário selecionando Origem = Solar e UF = MG
      result.current.apply({ ...EMPTY_FILTERS, origem: 'solar', uf: 'MG' });
    });

    expect(result.current.filters.origem).toBe('solar');
    expect(result.current.filters.uf).toBe('MG');
    expect(result.current.activeCount).toBe(2);
  });

  it('deve limpar todos os filtros ao chamar clear()', () => {
    // Inicializamos o router já com filtros na URL
    const wrapperComFiltros = ({ children }: { children: React.ReactNode }) => (
      <MemoryRouter initialEntries={['/?origem=eolica&uf=BA']}>
        {children}
      </MemoryRouter>
    );

    const { result } = renderHook(() => useFilters(), { wrapper: wrapperComFiltros });

    // Confirma que iniciou com os filtros da URL
    expect(result.current.filters.origem).toBe('eolica');
    expect(result.current.activeCount).toBe(2);

    act(() => {
      result.current.clear();
    });

    // Deve voltar ao estado vazio
    expect(result.current.filters).toEqual(EMPTY_FILTERS);
    expect(result.current.activeCount).toBe(0);
  });
});