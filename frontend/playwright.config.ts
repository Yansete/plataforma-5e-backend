import { defineConfig, devices } from '@playwright/test';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

/**
 * Pruebas de punta a punta (TA-001): levantan el backend real (FastAPI con una base SQLite nueva)
 * y el frontend (Vite), y recorren la plataforma en Chromium como lo haría un docente.
 *
 *   npm run test:e2e        (necesita Python con el backend instalado: pip install -e ../backend)
 *
 * La IA se reemplaza por el generador por reglas y la búsqueda por tema se desactiva, para que la
 * prueba no dependa de servicios externos. PYTHON permite elegir el intérprete (por defecto «python»).
 */
const FRONT = 5174;
const BACK = 8765;
const DB = join(tmpdir(), `plataforma-docente-e2e-${Date.now()}.db`).replace(/\\/g, '/');

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://localhost:${FRONT}`,
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `${process.env.PYTHON ?? 'python'} -m uvicorn platform5e.main:app --port ${BACK}`,
      cwd: '../backend',
      url: `http://127.0.0.1:${BACK}/salud`,
      env: { DATABASE_URL: `sqlite:///${DB}`, LLM_PROVIDER: 'rules', TOPIC_SEARCH_ENABLED: 'false', DEMO_CATALOG: 'false' },
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npx vite --port ${FRONT} --strictPort`,
      url: `http://localhost:${FRONT}`,
      env: { BACKEND_URL: `http://127.0.0.1:${BACK}` },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
