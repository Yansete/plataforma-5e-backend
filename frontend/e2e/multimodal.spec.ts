/**
 * Cambios pedidos por el docente (17/10): selección múltiple por etapa, recursos multimodales e interactivos,
 * revisión unificada en el orden de la clase, editor con formato y paquete SCORM con todos los recursos.
 */
import { expect, test, type Page } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const MATERIAL = fileURLToPath(new URL('./fixtures/protocols.txt', import.meta.url));
const SHOTS = (globalThis as unknown as { process: { env: Record<string, string | undefined> } }).process.env.SHOTS;

async function shot(page: Page, name: string) {
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
}

test('varios recursos por etapa: gráfico, audio y actividad, editados y exportados en SCORM', async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto('/');
  await page.getByRole('link', { name: 'Crear cuenta' }).click();
  await page.getByLabel('Nombre y apellido').fill('Ana Pérez');
  await page.getByLabel('Correo electrónico').fill(`ana.multi.${Date.now()}@correo.pe`);
  await page.getByLabel('Contraseña', { exact: true }).fill('clave-segura-1');
  await page.getByLabel('Repite la contraseña').fill('clave-segura-1');
  await page.getByRole('button', { name: 'Crear cuenta' }).click();
  await page.getByRole('link', { name: 'Nuevo curso' }).first().click();
  await page.getByLabel('Código').fill('MUL-101');
  await page.getByLabel('Nombre del curso').fill('Redes de Computadoras');
  await page.getByLabel('Periodo').fill('2026-II');
  await page.getByLabel('Título de la unidad').fill('Protocolos de transporte');
  await page.getByLabel('Resultados de aprendizaje').fill('Distingue las características de los protocolos TCP y UDP.');
  await page.getByRole('button', { name: 'Guardar curso' }).click();
  await page.getByRole('link', { name: 'Abrir unidad' }).click();
  await page.locator('input[type=file]').setInputFiles(MATERIAL);
  await page.getByLabel('Tengo permiso para usar este material en la plataforma.').check();
  await page.getByRole('button', { name: 'Subir y procesar' }).click();
  await expect(page.getByText(/quedó listo/)).toBeVisible();

  // Selección múltiple: un audio para iniciar, un mapa conceptual para explicar y un verdadero o falso para evaluar.
  await page.getByRole('link', { name: 'Continuar a Generación' }).click();
  await page.getByLabel('Preguntas de opción múltiple').uncheck();
  await page.getByLabel('Cápsula de audio detonante').check();
  await page.getByLabel('Mapa conceptual').check();
  await page.getByLabel('Verdadero o falso').check();
  await page.getByLabel('Cantidad').selectOption('1');
  await shot(page, 'm1-generacion-multiple');
  await page.getByRole('button', { name: 'Generar 3 recursos' }).click();
  await expect(page.getByText('Listo: 3 recursos para revisar')).toBeVisible({ timeout: 60_000 });

  // Revisión unificada en el orden de la clase.
  await page.getByRole('link', { name: 'Ir a Revisión' }).click();
  const headings = page.locator('.stage-group__title');
  await expect(headings).toHaveCount(3);
  await expect(headings.nth(0)).toContainText('Para iniciar la clase');
  await expect(headings.nth(1)).toContainText('Para explicar');
  await expect(headings.nth(2)).toContainText('Para evaluar');
  await expect(page.getByRole('img', { name: /Mapa conceptual/ })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Escuchar con la voz del navegador' })).toBeVisible();
  const quiz = page.locator('.review').filter({ hasText: 'Verdadero o falso:' });
  await expect(quiz.locator('.tag', { hasText: 'Falso' }).first()).toBeVisible();
  await shot(page, 'm2-revision-unificada');

  // Editor con formato en el mapa conceptual.
  const map = page.locator('.review').filter({ has: page.getByRole('img', { name: /Mapa conceptual/ }) });
  await map.getByRole('button', { name: 'Editar', exact: true }).click();
  const editor = map.locator('.rte__content');
  await expect(editor).toBeVisible();
  await editor.click();
  await page.keyboard.press('Control+End');
  await page.keyboard.type(' Idea importante');
  for (let i = 0; i < 'importante'.length; i++) await page.keyboard.press('Shift+ArrowLeft');
  await map.getByRole('button', { name: 'Negrita' }).click();
  await shot(page, 'm3-editor-enriquecido');
  await map.getByRole('button', { name: 'Guardar cambios' }).click();
  await expect(map.locator('.prose strong')).toHaveText('importante');

  // Elementos de la actividad.
  await quiz.getByRole('button', { name: 'Editar elementos' }).click();
  await quiz.getByLabel('Afirmación').first().fill('El protocolo TCP confirma la entrega de los datos.');
  await quiz.getByRole('button', { name: 'Guardar elementos' }).click();
  await expect(quiz.getByText('El protocolo TCP confirma la entrega de los datos.')).toBeVisible();

  for (const card of [page.locator('.review').first(), map, quiz]) {
    await card.getByRole('button', { name: 'Aprobar recurso' }).click();
  }
  await expect(page.getByRole('button', { name: 'Aprobados (3)' })).toBeVisible();

  // Un solo paquete SCORM con los tres recursos.
  await page.getByRole('link', { name: /Exportación/ }).click();
  await expect(page.getByText('3 seleccionados de 3')).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Descargar .zip' }).click();
  expect((await download).suggestedFilename()).toBe('mul-101-unidad-1-scorm.zip');
  await expect(page.getByRole('row').filter({ hasText: 'mul-101-unidad-1-scorm.zip' })).toContainText('3');
  await shot(page, 'm4-exportacion');
});
