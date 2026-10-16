/**
 * Pedido escrito: el docente describe lo que necesita y aquí se interpreta qué recurso pedir,
 * cuántos, con qué dificultad y para qué resultado de aprendizaje. El texto completo se envía
 * además como indicación, así que la interpretación solo fija los parámetros del pedido.
 */
import { hasOptions } from '@/features/generation/model/resourceCatalog';
import type { Difficulty, LearningOutcome, ResourceType, Unit } from '@/shared/types/domain';

export interface Interpretation {
  resourceType: ResourceType;
  quantity: number;
  difficulty: Difficulty;
  optionCount: number;
  /** null: todos los resultados de la unidad. */
  outcomeId: string | null;
}

export const MAX_REQUEST_LENGTH = 500;

/** Minúsculas y sin tildes, para comparar palabras. */
export function normalize(text: string): string {
  return text.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}

/** Frases que nombran un tipo sin ambigüedad. Se revisan en este orden. */
const EXPLICIT: [RegExp, ResourceType][] = [
  [/detonante/, 'pregunta_detonante'],
  [/opcion multiple/, 'item_opcion_multiple'],
  [/sondeo|ideas previas|saberes previos|conocimientos previos|diagnostic/, 'sondeo_diagnostico'],
  [/glosario|vocabulario|terminos clave/, 'glosario'],
  [/\b(un|una|el|los|unos|estudio de)\s+casos?\b|\bcasos? con\b|indagacion/, 'caso_indagacion'],
  [/guia de exploracion|guia para explorar/, 'guia_exploracion'],
];

/** Palabras generales: gana la que aparece primero en el pedido. */
const GENERAL: [RegExp, ResourceType][] = [
  [/\bpreguntas?\b|\bexamen\b|\bevalua|\bcuestionario|\bprueba\b|\bquiz|\bitems?\b|\balternativas\b|\bmarcar\b/, 'item_opcion_multiple'],
  [/\bejercicios?\b|\bpractica\b|\bproblemas?\b|\baplica/, 'ejercicio_aplicacion'],
  [/\bexplica|\bresumen\b|\bsintesis\b|\bteoria\b/, 'explicacion'],
  [/\bguias?\b|\bexplora/, 'guia_exploracion'],
  [/iniciar la clase|empezar la clase|motivar/, 'pregunta_detonante'],
];

export function detectType(text: string): ResourceType {
  const t = normalize(text);
  for (const [pattern, type] of EXPLICIT) if (pattern.test(t)) return type;
  let best: { index: number; type: ResourceType } | null = null;
  for (const [pattern, type] of GENERAL) {
    const index = t.search(pattern);
    if (index >= 0 && (!best || index < best.index)) best = { index, type };
  }
  return best?.type ?? 'explicacion';
}

const NUMBERS: Record<string, number> = { un: 1, una: 1, uno: 1, dos: 2, tres: 3, cuatro: 4, cinco: 5, seis: 6, siete: 7, ocho: 8, nueve: 9, diez: 10 };
const NUMBER = `(\\d+|${Object.keys(NUMBERS).join('|')})`;
const RESOURCE_NOUN = '(preguntas?|items?|ejercicios?|casos?|guias?|explicacion(?:es)?|glosarios?|sondeos?|recursos?|problemas?|reactivos?)';

function toNumber(word: string): number {
  return /^\d+$/.test(word) ? Number(word) : NUMBERS[word] ?? 0;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** Cantidad pedida (1 a 5). Sin número: 3 si el pedido está en plural, 1 si no. */
export function detectQuantity(text: string): number {
  const t = normalize(text);
  const match = t.match(new RegExp(`\\b${NUMBER}\\s+(?:\\w+\\s+)?${RESOURCE_NOUN}\\b`));
  if (match) return clamp(toNumber(match[1]), 1, 5);
  return new RegExp(`\\b${RESOURCE_NOUN}\\b`).exec(t)?.[1]?.match(/s$|es$/) ? 3 : 1;
}

/** Alternativas por pregunta (3 a 5), si el pedido las indica. */
export function detectOptionCount(text: string): number {
  const match = normalize(text).match(new RegExp(`\\b${NUMBER}\\s+(alternativas|opciones|respuestas)\\b`));
  return match ? clamp(toNumber(match[1]), 3, 5) : 4;
}

export function detectDifficulty(text: string): Difficulty {
  const t = normalize(text);
  if (/intermedi|\bmedia\b|\bmedio\b/.test(t)) return 'intermedia';
  if (/dificil|avanzad|complej|exigente|reto\b/.test(t)) return 'avanzada';
  if (/facil|basic|sencill|simple|introductori/.test(t)) return 'basica';
  return 'intermedia';
}

const STOPWORDS = new Set(
  'los las del que con para una por como sus mis entre sobre esta este estos estas desde cada donde cual cuales son ser muy mas sin hacia hasta pero tambien'.split(' '),
);

function words(text: string): Set<string> {
  return new Set(normalize(text).split(/[^a-z0-9]+/).filter((w) => w.length >= 3 && !STOPWORDS.has(w)));
}

/** Raíz corta para que «distinguen» coincida con «distingue». */
function stem(word: string): string {
  return word.length > 5 ? word.slice(0, 5) : word;
}

/** Resultado de aprendizaje al que apunta el pedido: por su código (RA1.2) o por las palabras en común. */
export function detectOutcome(text: string, outcomes: LearningOutcome[]): string | null {
  const t = normalize(text);
  const byCode = outcomes.find((o) => o.code && new RegExp(`\\b${normalize(o.code).replace(/\./g, '\\.')}\\b`).test(t));
  if (byCode) return byCode.id;
  const asked = new Set([...words(text)].map(stem));
  let best: { id: string; score: number } | null = null;
  for (const o of outcomes) {
    const score = [...words(o.text)].map(stem).filter((w) => asked.has(w)).length;
    if (score >= 2 && (!best || score > best.score)) best = { id: o.id, score };
  }
  return best?.id ?? null;
}

export function interpretRequest(text: string, outcomes: LearningOutcome[]): Interpretation {
  const resourceType = detectType(text);
  return {
    resourceType,
    quantity: detectQuantity(text),
    difficulty: detectDifficulty(text),
    optionCount: hasOptions(resourceType) ? detectOptionCount(text) : 4,
    outcomeId: detectOutcome(text, outcomes),
  };
}

/** Ideas para empezar a escribir, con el tema de la unidad. */
export function suggestions(unit: Pick<Unit, 'title' | 'outcomes'>): string[] {
  const first = unit.outcomes[0];
  return [
    'Una pregunta detonante para iniciar la clase',
    'Un glosario con los términos clave',
    `Un caso para explorar «${unit.title}»`,
    first ? `3 preguntas de opción múltiple para evaluar ${first.code}` : '3 preguntas de opción múltiple para evaluar la unidad',
  ];
}
