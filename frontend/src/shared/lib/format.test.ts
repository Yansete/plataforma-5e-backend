/**
 * TA-008 · Pruebas de caja blanca de los formatos que ve el docente (fechas, tamaños y plurales).
 */
import { describe, expect, it } from 'vitest';
import { formatBytes, formatDate, formatDateTime, plural } from '@/shared/lib/format';

describe('formatos de la interfaz', () => {
  it('muestra un guion cuando no hay fecha', () => {
    expect(formatDateTime(null)).toBe('—');
    expect(formatDate(null)).toBe('—');
  });

  it('formatea fechas en español', () => {
    // La hora depende de la zona horaria del equipo, por eso solo se comprueba el año y el mes.
    expect(formatDate('2026-10-09T15:00:00Z')).toMatch(/2026/);
    expect(formatDate('2026-10-09T15:00:00Z').toLowerCase()).toMatch(/oct/);
    expect(formatDateTime('2026-10-09T15:00:00Z')).toMatch(/2026/);
  });

  it('elige la unidad de tamaño adecuada', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(1023)).toBe('1023 B');
    expect(formatBytes(2048)).toBe('2 KB');
    expect(formatBytes(1.5 * 1024 * 1024)).toBe('1,5 MB');
  });

  it('usa singular solo para uno', () => {
    expect(plural(1, 'ítem', 'ítems')).toBe('1 ítem');
    expect(plural(0, 'ítem', 'ítems')).toBe('0 ítems');
    expect(plural(3, 'ítem', 'ítems')).toBe('3 ítems');
  });
});
