/** Pedido escrito: qué entiende la plataforma de lo que escribe el docente. */
import { describe, expect, it } from 'vitest';
import { detectDifficulty, detectOptionCount, detectOutcome, detectQuantity, detectType, interpretRequest, normalize, suggestions } from '@/features/generation/model/requestInterpreter';
import { unit } from '@/test/fixtures';

describe('tipo de recurso', () => {
  it.each([
    ['Necesito 3 preguntas de opción múltiple para evaluar TCP y UDP', 'item_opcion_multiple'],
    ['Una pregunta detonante para iniciar la clase', 'pregunta_detonante'],
    ['Un glosario con los términos clave', 'glosario'],
    ['Un caso para explorar la encapsulación', 'caso_indagacion'],
    ['Un ejercicio para elegir entre TCP y UDP', 'ejercicio_aplicacion'],
    ['Un ejercicio para evaluar si aplican TCP', 'ejercicio_aplicacion'],
    ['Un sondeo de ideas previas', 'sondeo_diagnostico'],
    ['Una guía de exploración del modelo', 'guia_exploracion'],
    ['Explica la encapsulación con un ejemplo', 'explicacion'],
    ['Algo para motivar al inicio, para empezar la clase', 'pregunta_detonante'],
    ['Quiero material sobre redes', 'explicacion'],
  ])('«%s» → %s', (request, type) => {
    expect(detectType(request)).toBe(type);
  });
});

describe('cantidad, alternativas y dificultad', () => {
  it('lee números en cifras o en palabras', () => {
    expect(detectQuantity('Necesito 3 preguntas')).toBe(3);
    expect(detectQuantity('dos buenas preguntas')).toBe(2);
    expect(detectQuantity('quiero 12 ejercicios')).toBe(5);
    expect(detectQuantity('Una pregunta detonante')).toBe(1);
    expect(detectQuantity('preguntas sobre las 5 capas')).toBe(3);
    expect(detectQuantity('un glosario')).toBe(1);
    expect(detectQuantity('algo sobre redes')).toBe(1);
  });

  it('lee las alternativas por pregunta', () => {
    expect(detectOptionCount('3 preguntas con cinco alternativas')).toBe(5);
    expect(detectOptionCount('con 2 opciones')).toBe(3);
    expect(detectOptionCount('preguntas')).toBe(4);
  });

  it('lee la dificultad', () => {
    expect(detectDifficulty('de dificultad intermedia')).toBe('intermedia');
    expect(detectDifficulty('preguntas difíciles')).toBe('avanzada');
    expect(detectDifficulty('algo fácil para empezar')).toBe('basica');
    expect(detectDifficulty('preguntas sobre multimedia')).toBe('intermedia');
  });
});

describe('resultado de aprendizaje', () => {
  const outcomes = unit().outcomes;

  it('lo reconoce por su código o por las palabras en común', () => {
    expect(detectOutcome('preguntas para RA1.2', outcomes)).toBe('ra2');
    expect(detectOutcome('para evaluar si mis estudiantes distinguen TCP y UDP', outcomes)).toBe('ra1');
    expect(detectOutcome('algo sobre redes', outcomes)).toBeNull();
  });

  it('interpreta el pedido completo', () => {
    expect(interpretRequest('Necesito 3 preguntas de opción múltiple con 5 alternativas para evaluar si distinguen TCP y UDP, dificultad intermedia.', outcomes)).toEqual({
      resourceType: 'item_opcion_multiple',
      quantity: 3,
      difficulty: 'intermedia',
      optionCount: 5,
      outcomeId: 'ra1',
    });
    expect(interpretRequest('Un glosario con 5 alternativas', outcomes)).toMatchObject({ resourceType: 'glosario', optionCount: 4 });
    expect(detectType('Un ejercicio con alternativas de solución')).toBe('ejercicio_aplicacion');
  });

  it('propone ideas con el tema de la unidad', () => {
    const ideas = suggestions(unit());
    expect(ideas).toHaveLength(4);
    expect(ideas[2]).toContain('Modelo TCP/IP');
    expect(ideas[3]).toContain('RA1.1');
    expect(suggestions(unit({ outcomes: [] }))[3]).toMatch(/la unidad/);
    expect(normalize('Opción MÚLTIPLE')).toBe('opcion multiple');
  });
});
