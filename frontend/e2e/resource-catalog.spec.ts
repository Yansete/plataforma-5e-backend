/** HU-006: opciones recibidas del backend y recuperación ante un fallo del catálogo. */
import { expect, test } from '@playwright/test';
import { fileURLToPath } from 'node:url';

test('carga el catálogo publicado y permite reintentar sin usar una lista local', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Crear cuenta' }).click();
  await page.getByLabel('Nombre y apellido').fill('Ana Catálogo');
  await page.getByLabel('Correo electrónico').fill(`catalog.${Date.now()}@correo.pe`);
  await page.getByLabel('Contraseña', { exact: true }).fill('clave-segura-1');
  await page.getByLabel('Repite la contraseña').fill('clave-segura-1');
  await page.getByRole('button', { name: 'Crear cuenta' }).click();
  await page.getByRole('link', { name: 'Nuevo curso' }).first().click();
  await page.getByLabel('Código').fill('CAT-006');
  await page.getByLabel('Nombre del curso').fill('Redes');
  await page.getByLabel('Periodo').fill('2026-II');
  await page.getByLabel('Título de la unidad').fill('Protocolos');
  await page.getByLabel('Resultados de aprendizaje').fill('Distingue TCP y UDP');
  await page.getByRole('button', { name: 'Guardar curso' }).click();
  await page.getByRole('link', { name: 'Abrir unidad' }).click();
  await page.locator('input[type=file]').setInputFiles(fileURLToPath(new URL('./fixtures/protocols.txt', import.meta.url)));
  await page.getByLabel('Tengo permiso para usar este material en la plataforma.').check();
  await page.getByRole('button', { name: 'Subir y procesar' }).click();
  await expect(page.getByText(/quedó listo/)).toBeVisible();

  let calls = 0;
  await page.route('**/api/v1/resource-types', async (route) => {
    if (++calls === 1) {
      await route.fulfill({ status: 503, json: { error: { code: 'CATALOG_UNAVAILABLE', message: 'Catálogo temporalmente no disponible.' } } });
      return;
    }
    const response = await route.fetch();
    const catalog = await response.json();
    for (const entry of catalog) if (entry.id === 'glosario') {
      entry.name = 'Glosario publicado por el backend';
      entry.count = ['término de catálogo', 'términos de catálogo'];
    }
    await route.fulfill({ response, json: catalog });
  });
  await page.getByRole('link', { name: 'Continuar a Generación' }).click();
  await expect(page.getByRole('alert')).toContainText('Catálogo temporalmente no disponible.');
  await expect(page.getByRole('checkbox', { name: 'Preguntas de opción múltiple' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Reintentar', exact: true }).click();
  await expect(page.getByRole('checkbox')).toHaveCount(18);
  await expect(page.getByLabel('Glosario publicado por el backend', { exact: true })).toBeVisible();
  await page.getByLabel('Preguntas de opción múltiple', { exact: true }).uncheck();
  await page.getByLabel('Glosario publicado por el backend', { exact: true }).check();
  await expect(page.getByRole('button', { name: 'Generar 2 términos de catálogo', exact: true })).toBeVisible();
  expect(calls).toBe(2);
});
