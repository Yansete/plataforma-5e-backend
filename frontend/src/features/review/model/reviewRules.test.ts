import { describe, expect, it } from 'vitest';
import { citedCount, citedEvidence, countByStatus, editContent, editOption, editProblem, highlight, optionProblem, optionSource, setStatus, withStatus } from '@/features/review/model/reviewRules';
import { item, text } from '@/test/fixtures';

describe('reglas para aprobar', () => {
  it('cuenta y ordena por estado', () => {
    const list = [item({ id: 'a', createdAt: '2026-01-01' }), item({ id: 'b', createdAt: '2026-02-01' }), text({ status: 'aprobado' })];
    expect(countByStatus(list)).toEqual({ pendiente: 2, aprobado: 1, descartado: 0 });
    expect(withStatus(list, 'pendiente').map((r) => r.id)).toEqual(['b', 'a']);
  });
});

describe('cambios del docente', () => {
  it('editar un distractor lo acepta y marca la edición', () => {
    const r = editOption(item(), 'b', 'TCP con acuse', 'Retro b');
    expect(r.options![1]).toMatchObject({ text: 'TCP con acuse', edited: true, decision: 'aceptado' });
    const same = editOption(item(), 'b', 'TCP', 'Retro b');
    expect(same.options![1]).toMatchObject({ edited: false, decision: 'aceptado' });
    const key = editOption(item(), 'a', 'UDP', 'Nueva retro');
    expect(key.options![0]).toMatchObject({ decision: 'pendiente', edited: true });
  });

  it('editar el contenido y cambiar el estado', () => {
    expect(editContent(text(), 'Las capas del modelo', 'Primer párrafo.\n\nSegundo <párrafo>.').edited).toBe(false);
    expect(editContent(text(), 'Otro título', text().body).edited).toBe(true);
    expect(setStatus(item(), 'descartado')).toMatchObject({ status: 'descartado', discardReason: 'otro' });
    expect(setStatus(item({ status: 'descartado', discardReason: 'duplicado' }), 'pendiente')).toMatchObject({ status: 'pendiente', discardReason: null });
  });

  it('valida los textos editados', () => {
    expect(editProblem('', 'x')).toMatch(/título/);
    expect(editProblem('T', ' ')).toMatch(/vacío/);
    expect(editProblem('x'.repeat(161), 'x')).toMatch(/160/);
    expect(editProblem('T', 'x'.repeat(8001))).toMatch(/8000/);
    expect(editProblem('T', 'x')).toBeNull();
    expect(optionProblem(' ', '')).toMatch(/texto/);
    expect(optionProblem('x', 'y'.repeat(601))).toMatch(/600/);
    expect(optionProblem('x', '')).toBeNull();
  });
});

describe('evidencia', () => {
  it('relaciona cada afirmación con sus fragmentos guardados', () => {
    const r = item();
    expect(citedEvidence(r).map((c) => [c.claim, c.evidence.map((e) => e.id)])).toEqual([
      ['TCP garantiza una entrega confiable y retransmite lo que se pierde', ['f1']],
      ['UDP introduce menos retardo', ['f2']],
    ]);
    expect(citedEvidence(item({ citations: [{ claim: 'sin fuente', fragmentIds: ['x'] }] }))).toEqual([]);
    expect(optionSource(r, r.options![0])?.id).toBe('f2');
    expect(optionSource(r, r.options![3])).toBeNull();
    expect(citedCount(r)).toBe(2);
  });

  it('resalta la frase del fragmento que sostiene la afirmación', () => {
    const [before, match, after] = highlight('TCP numera los segmentos. TCP garantiza una entrega confiable porque confirma la recepción. Es más lento.', 'TCP garantiza una entrega confiable');
    expect(before).toBe('TCP numera los segmentos. ');
    expect(match).toBe('TCP garantiza una entrega confiable porque confirma la recepción.');
    expect(after).toBe(' Es más lento.');
    expect(highlight('Nada que ver aquí.', 'TCP garantiza entrega')).toEqual(['Nada que ver aquí.', '', '']);
  });
});
