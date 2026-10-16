/**
 * Recorrido completo de un docente con el backend real:
 * crear cuenta → curso → material → generación (opciones y pedido) → revisión → descargas → borrar curso.
 */
import { expect, test, type Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const MATERIAL = fileURLToPath(new URL('./archivos/protocolos.txt', import.meta.url));
const CLAVE = 'clave-segura-1';

async function crearCuenta(page: Page, correo: string) {
  await page.goto('/');
  await expect(page).toHaveURL(/\/entrar$/);
  await page.getByRole('link', { name: 'Crear cuenta' }).click();
  await page.getByLabel('Nombre y apellido').fill('Ana Pérez');
  await page.getByLabel('Correo electrónico').fill(correo);
  await page.getByLabel('Contraseña', { exact: true }).fill(CLAVE);
  await page.getByLabel('Repite la contraseña').fill(CLAVE);
  await page.getByRole('button', { name: 'Crear cuenta' }).click();
  await expect(page.getByRole('heading', { name: 'Mis cursos' })).toBeVisible();
}

async function crearCurso(page: Page, codigo: string) {
  await page.getByRole('link', { name: 'Nuevo curso' }).first().click();
  await page.getByLabel('Código').fill(codigo);
  await page.getByLabel('Nombre del curso').fill('Redes de Computadoras');
  await page.getByLabel('Periodo').fill('2026-II');
  await page.getByLabel('Título de la unidad').fill('Protocolos de transporte');
  await page.getByLabel('Resultados de aprendizaje').fill('Distingue las características de los protocolos TCP y UDP.\nExplica la encapsulación.');
  await page.getByRole('button', { name: 'Guardar curso' }).click();
  await expect(page.getByRole('heading', { name: 'Redes de Computadoras' })).toBeVisible();
  await expect(page.getByText('Sin material todavía.')).toBeVisible();
}

test('la pantalla de inicio solo pide correo y contraseña, y avisa si son incorrectos', async ({ page }) => {
  await page.goto('/cursos/cualquiera');
  await expect(page).toHaveURL(/\/entrar$/);
  await expect(page.getByRole('heading', { name: 'Inicio de sesión' })).toBeVisible();
  await expect(page.getByText(/modo de acceso|demo|prototipo/i)).toHaveCount(0);
  await page.getByLabel('Correo electrónico').fill('nadie@correo.pe');
  await page.getByLabel('Contraseña').fill('equivocada');
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page.getByRole('alert')).toContainText('Correo o contraseña incorrectos.');
});

test('recorrido del docente: del curso a la descarga, con todo guardado en el servidor', async ({ page }) => {
  const correo = `ana.${Date.now()}@correo.pe`;
  await crearCuenta(page, correo);
  await expect(page.getByText('Todavía no tienes cursos')).toBeVisible();
  await crearCurso(page, 'E2E-101');

  // Material
  await page.getByRole('link', { name: 'Abrir unidad' }).click();
  await expect(page.getByRole('heading', { name: 'Protocolos de transporte' })).toBeVisible();
  await page.getByRole('link', { name: /Generación/ }).click();
  await expect(page.getByText('Primero agrega material a la unidad')).toBeVisible();
  await page.getByRole('link', { name: 'Ir a Material' }).click();
  await page.locator('input[type=file]').setInputFiles(MATERIAL);
  await page.getByRole('button', { name: 'Subir y procesar' }).click();
  await expect(page.getByRole('alert')).toContainText('Confirma que tienes permiso');
  await page.getByLabel('Tengo permiso para usar este material en la plataforma.').check();
  await page.getByRole('button', { name: 'Subir y procesar' }).click();
  await expect(page.getByText(/quedó listo/)).toBeVisible();
  await expect(page.getByText(/Procesado · \d+ fragmentos?/)).toBeVisible();
  await page.getByRole('button', { name: 'Ver fragmentos' }).click();
  await expect(page.getByText('Fragmento 1 · ')).toBeVisible();

  // La búsqueda por tema está desactivada en esta prueba: el docente ve el motivo.
  await page.getByLabel('Tema').fill('Protocolo TCP');
  await page.getByRole('button', { name: 'Buscar y procesar' }).click();
  await expect(page.getByRole('alert')).toContainText('no está activada');

  // Generación con opciones
  await page.getByRole('link', { name: 'Continuar a Generación' }).click();
  await page.getByLabel('Preguntas de opción múltiple').check();
  await page.getByLabel('Cantidad').selectOption('1');
  await page.getByRole('button', { name: 'Generar 1 pregunta' }).click();
  await expect(page.getByText('Listo: 1 pregunta para revisar')).toBeVisible();
  await expect(page.getByRole('link', { name: /Revisión/ }).first()).toContainText('1 por revisar');

  // Generación con pedido escrito
  await page.getByRole('button', { name: 'Escribir pedido' }).click();
  await page.getByRole('button', { name: 'Un glosario con los términos clave' }).click();
  await expect(page.getByText('Así entendí tu pedido')).toBeVisible();
  await expect(page.locator('.understood')).toContainText('Glosario');
  await page.getByRole('button', { name: 'Generar 1 glosario' }).click();
  await expect(page.getByText('Listo: 1 glosario para revisar')).toBeVisible();

  // Revisión
  await page.getByRole('link', { name: 'Ir a Revisión' }).click();
  await expect(page.getByRole('button', { name: 'Por revisar (2)' })).toBeVisible();
  const pregunta = page.locator('.review').filter({ has: page.locator('.options') });
  await expect(pregunta.getByRole('button', { name: 'Aprobar recurso' })).toBeDisabled();
  await expect(pregunta).toContainText('distractores pendientes');
  const aceptar = pregunta.getByRole('button', { name: 'Aceptar' });
  while ((await aceptar.count()) > 0) {
    const antes = await aceptar.count();
    await aceptar.first().click();
    await expect(aceptar).toHaveCount(antes - 1);
  }
  await pregunta.getByRole('button', { name: 'Aprobar recurso' }).click();
  await expect(page.getByRole('button', { name: 'Aprobados (1)' })).toBeVisible();
  const glosario = page.locator('.review').first();
  await glosario.getByRole('button', { name: 'Descartar recurso' }).click();
  await glosario.getByLabel('¿Por qué lo descartas?').selectOption('fuera_de_unidad');
  await glosario.getByRole('button', { name: 'Descartar recurso' }).click();
  await expect(page.getByRole('button', { name: 'Descartados (1)' })).toBeVisible();

  // Lo revisado queda guardado en el servidor.
  await page.reload();
  await expect(page.getByRole('button', { name: 'Aprobados (1)' })).toBeVisible();
  await expect(page.getByText('1 recurso aprobado')).toBeVisible();

  // Exportación
  await page.getByRole('link', { name: /Exportación/ }).click();
  await expect(page.getByText('Recursos aprobados de esta unidad')).toBeVisible();
  const descarga = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Descargar .xml' }).click();
  const archivo = await descarga;
  expect(archivo.suggestedFilename()).toBe('e2e-101-unidad-1-moodle.xml');
  const xml = await readFile(await archivo.path(), 'utf-8');
  expect(xml).toContain('<quiz>');
  expect(xml).toContain('$course$/top/E2E-101 · Unidad 1');
  await expect(page.getByRole('cell', { name: 'e2e-101-unidad-1-moodle.xml' })).toBeVisible();
  await page.getByRole('button', { name: 'Borrar historial' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Borrar historial' }).click();
  await expect(page.getByText('Todavía no hay descargas de esta unidad.')).toBeVisible();

  // Cerrar sesión y volver a entrar: los datos siguen ahí.
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await expect(page).toHaveURL(/\/entrar$/);
  await page.getByLabel('Correo electrónico').fill(correo);
  await page.getByLabel('Contraseña').fill(CLAVE);
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page.getByText('1 recurso aprobado')).toBeVisible();

  // Borrar el curso
  await page.getByRole('link', { name: 'Editar' }).click();
  await page.getByRole('button', { name: 'Borrar curso' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Borrar curso' }).click();
  await expect(page.getByText('Todavía no tienes cursos')).toBeVisible();
});

test('en el celular el menú se abre y se cierra con Escape', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await crearCuenta(page, `movil.${Date.now()}@correo.pe`);
  await page.getByRole('button', { name: 'Menú', exact: true }).click();
  await expect(page.getByRole('navigation', { name: 'Navegación principal' }).getByRole('link', { name: 'Mis cursos' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Menú', exact: true })).toBeFocused();
});
