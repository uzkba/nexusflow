import { test, expect } from '@playwright/test';

// Massa de dados mockada para as requisições GET do frontend
const mockPendencias = [
  {
    id: '1',
    ceg: 'UFV-12345',
    tipo: 'alteracao_dado',
    diff_pendente: {
      potencia_outorgada_kw: {
        valor_antigo: 15000,
        valor_novo: 20000
      }
    }
  },
  {
    id: '2',
    ceg: 'EOL-98765',
    tipo: 'consolidacao',
    cegs_relacionados: ['EOL-98765-OLD', 'EOL-98765-BETA'],
    score_similaridade: 95.5
  }
];

test.describe('Aprovação de Consolidação e Pendências', () => {
  
  test.beforeEach(async ({ page }) => {
    // 1. Intercepta a requisição GET inicial usando a ROTA CORRETA DO SEU HOOK
    await page.route('**/api/consolidacoes/pendentes', async (route) => {
      await route.fulfill({ status: 200, json: mockPendencias });
    });

    // 2. Acessa a página INICIAL (raiz) onde o seu painel realmente fica
    await page.goto('http://localhost:5173/aprovacao-consolidacao');
  });

  test('deve listar as pendências corretamente (alteração e consolidação)', async ({ page }) => {
    // Verifica se os textos do PainelPendencias apareceram
    await expect(page.getByText('Revisão de Pendências')).toBeVisible();

    // Verifica o Card de Alteração de Dado
    await expect(page.getByText('UFV-12345')).toBeVisible();
    await expect(page.getByText('Alteração de Dados')).toBeVisible();
    
    // Verifica se o DiffViewer renderizou os valores
    await expect(page.getByText('15000')).toBeVisible();
    await expect(page.getByText('20000')).toBeVisible();

    // Verifica o Card de Consolidação
    await expect(page.getByText('EOL-98765', { exact: true })).toBeVisible();
    await expect(page.getByText('Consolidação', { exact: true })).toBeVisible();
    await expect(page.getByText('EOL-98765-OLD')).toBeVisible();
    await expect(page.getByText('95.50%')).toBeVisible();
  });

  test('deve simular aprovação de alteração e remoção do card (invalidação de cache)', async ({ page }) => {
    // Intercepta e mocka o PATCH de aprovação para a pendência ID 1
    await page.route('**/api/consolidacoes/1/aprovar', async (route) => {
      // Pequeno atraso para podermos ver o botão mudar para "Aprovando..."
      await new Promise(resolve => setTimeout(resolve, 500));
      await route.fulfill({ status: 200, json: { success: true } });
    });

    const cardAlteracao = page.locator('.rounded-lg', { hasText: 'UFV-12345' });
    
    // Clica no botão Aprovar DENTRO deste card específico
    const btnAprovar = cardAlteracao.getByRole('button', { name: 'Aprovar' });
    await btnAprovar.click();

    // Verifica o estado de loading do botão
    await expect(cardAlteracao.getByRole('button', { name: 'Aprovando...' })).toBeVisible();

    // Quando o React Query invalidar o cache, interceptamos o NOVO GET na ROTA CORRETA
    await page.route('**/api/consolidacoes/pendentes', async (route) => {
      await route.fulfill({ status: 200, json: [mockPendencias[1]] });
    });

    // Resultado final: o card da UFV-12345 deve sumir da tela!
    await expect(cardAlteracao).not.toBeVisible();
    // O outro card deve continuar lá
    await expect(page.getByText('EOL-98765', { exact: true })).toBeVisible();
  });

  test('deve simular rejeição de consolidação', async ({ page }) => {
    // 1. Intercepta e mocka o PATCH de rejeição para a pendência ID 2
    await page.route('**/api/consolidacoes/2/rejeitar', async (route) => {
      await route.fulfill({ status: 200, json: { success: true } });
    });

    // 👇 A MUDANÇA É AQUI: Prepara o NOVO GET (retornando vazio) ANTES de clicar!
    await page.route('**/api/consolidacoes/pendentes', async (route) => {
      await route.fulfill({ status: 200, json: [] });
    });

    const cardConsolidacao = page.locator('.rounded-lg', { hasText: 'EOL-98765' });
    const btnRejeitar = cardConsolidacao.getByRole('button', { name: 'Rejeitar' });
    
    // 2. Agora sim, clica no botão. O refetch vai cair no mock vazio que preparamos acima.
    await btnRejeitar.click();

    // 3. Verifica se a tela de estado vazio apareceu
    await expect(page.getByText('Nenhuma pendência na fila de revisão no momento.')).toBeVisible();
  });

});