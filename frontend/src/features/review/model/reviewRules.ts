import type { DiscardReason, DistractorDecision, Evidence, ItemOption, Resource, ReviewStatus } from '@/shared/types/domain';

export function countByStatus(resources: Resource[]): Record<ReviewStatus, number> {
  const counts: Record<ReviewStatus, number> = { pendiente: 0, aprobado: 0, descartado: 0 };
  for (const r of resources) counts[r.status] += 1;
  return counts;
}

/** Más recientes primero. */
export function withStatus(resources: Resource[], status: ReviewStatus): Resource[] {
  return resources.filter((r) => r.status === status).sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

/* ——— Cambios locales (puros): la página los aplica y luego guarda ——— */

function changeOption(resource: Resource, optionId: string, change: (o: ItemOption) => ItemOption): Resource {
  return { ...resource, options: (resource.options ?? []).map((o) => (o.id === optionId ? change(o) : o)) };
}

export function decideOption(resource: Resource, optionId: string, decision: DistractorDecision, reason: DiscardReason | null = null): Resource {
  return changeOption(resource, optionId, (o) => ({ ...o, decision, discardReason: decision === 'descartado' ? reason ?? 'otro' : null }));
}

/** Editar un distractor también lo acepta: el docente ya lo dejó como quería. */
export function editOption(resource: Resource, optionId: string, text: string, feedback: string): Resource {
  return changeOption(resource, optionId, (o) => ({
    ...o,
    text,
    feedback,
    edited: o.edited || text !== o.text || feedback !== o.feedback,
    decision: o.isCorrect ? o.decision : 'aceptado',
    discardReason: null,
  }));
}

export function editContent(resource: Resource, title: string, body: string): Resource {
  const changed = title !== resource.title || body !== resource.body;
  return { ...resource, title, body, edited: resource.edited || changed };
}

export function setStatus(resource: Resource, status: ReviewStatus, reason: DiscardReason | null = null): Resource {
  return { ...resource, status, discardReason: status === 'descartado' ? reason ?? 'otro' : null };
}

/** Problema de un texto editado, o null si se puede guardar. */
export function editProblem(title: string, body: string): string | null {
  if (!title.trim()) return 'Escribe un título.';
  if (!body.trim()) return 'El contenido no puede estar vacío.';
  if (title.length > 160) return 'El título puede tener hasta 160 caracteres.';
  if (body.length > 8000) return 'El contenido puede tener hasta 8000 caracteres.';
  return null;
}

export function optionProblem(text: string, feedback: string): string | null {
  if (!text.trim()) return 'Escribe el texto de la alternativa.';
  if (text.length > 600 || feedback.length > 600) return 'La alternativa y su retroalimentación pueden tener hasta 600 caracteres.';
  return null;
}

/* ——— Evidencia ——— */

export function evidenceById(resource: Resource): Map<string, Evidence> {
  return new Map(resource.evidence.map((e) => [e.id, e]));
}

/** Cada afirmación citada con los fragmentos que la sostienen. */
export function citedEvidence(resource: Resource): { claim: string; evidence: Evidence[] }[] {
  const byId = evidenceById(resource);
  return resource.citations
    .map((c) => ({ claim: c.claim, evidence: c.fragmentIds.map((id) => byId.get(id)).filter((e): e is Evidence => Boolean(e)) }))
    .filter((c) => c.evidence.length > 0);
}

/** Fragmento de donde sale una alternativa, para el enlace «Ver origen». */
export function optionSource(resource: Resource, option: ItemOption): Evidence | null {
  const byId = evidenceById(resource);
  for (const id of option.sourceFragmentIds) {
    const evidence = byId.get(id);
    if (evidence) return evidence;
  }
  return null;
}

/** Número de fragmentos distintos que cita el recurso. */
export function citedCount(resource: Resource): number {
  return resource.evidence.length;
}

function sentenceWords(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .split(/[^a-z0-9]+/)
      .filter((w) => w.length >= 4),
  );
}

/**
 * Parte del fragmento que más se parece a la afirmación, para resaltarla.
 * Devuelve el texto en tres partes: antes, resaltado y después.
 */
export function highlight(text: string, claim: string): [string, string, string] {
  const wanted = sentenceWords(claim);
  let best: { start: number; end: number; score: number } | null = null;
  for (const m of text.matchAll(/[^.!?…]+[.!?…]*/g)) {
    const score = [...sentenceWords(m[0])].filter((w) => wanted.has(w)).length;
    if (score >= 2 && (!best || score > best.score)) {
      const leading = m[0].length - m[0].trimStart().length;
      const index = m.index ?? 0;
      best = { start: index + leading, end: index + m[0].trimEnd().length, score };
    }
  }
  if (!best) return [text, '', ''];
  return [text.slice(0, best.start), text.slice(best.start, best.end), text.slice(best.end)];
}
