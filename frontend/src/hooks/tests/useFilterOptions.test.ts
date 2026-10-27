import { renderHook } from '@testing-library/react';
import { useFilterOptions } from '../use-filter-options'; // Ajuste o caminho se necessário

describe('useFilterOptions Hook', () => {
  it('deve retornar as opções estáticas corretamente (origens e UFs)', () => {
    // Renderiza o hook passando uma UF vazia no início
    const { result } = renderHook(() => useFilterOptions(''));

    // Verifica origens
    expect(result.current.origens).toHaveLength(2);
    expect(result.current.origens[0]).toEqual({ value: 'solar', label: 'Solar' });

    // Verifica UFs (temos 27 estados na constante UFS)
    expect(result.current.ufs).toHaveLength(27);
    expect(result.current.ufs).toContainEqual({ value: 'SP', label: 'SP' });
  });

  it('deve gerar dinamicamente os últimos e próximos anos baseados no ano atual', () => {
    const { result } = renderHook(() => useFilterOptions(''));
    
    const anoAtual = new Date().getFullYear();
    const anoMaisAlto = String(anoAtual + 5);
    
    expect(result.current.anos).toHaveLength(15);
    // O primeiro ano da lista deve ser o ano atual + 5
    expect(result.current.anos[0].value).toBe(anoMaisAlto);
  });

  it('deve retornar arrays vazios para as opções que dependem de TODOs da API', () => {
    const { result } = renderHook(() => useFilterOptions('SP'));

    expect(result.current.clientes).toEqual([]);
    expect(result.current.projetos).toEqual([]);
    expect(result.current.municipios).toEqual([]);
  });
});