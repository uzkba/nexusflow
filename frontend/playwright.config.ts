import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  // Aponta para a pasta onde você salvou o consolidacao.spec.ts
  testDir: './tests', 
  fullyParallel: true,
  reporter: 'html',
  
  use: {
    // Aqui está a mágica: ensinamos ao Playwright qual é a URL raiz do seu projeto
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
  },
  
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});