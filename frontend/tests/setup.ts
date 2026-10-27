// tests/setup.ts
import '@testing-library/jest-dom/vitest'; // Correção para o erro de tipos
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

afterEach(() => {
  cleanup();
});