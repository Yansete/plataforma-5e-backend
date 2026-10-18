/**
 * HTML del editor enriquecido en el navegador: se limpia antes de mostrarlo (además de la limpieza del servidor)
 * y se convierte a texto para la versión sin formato que usan la aprobación, la búsqueda y la IA.
 */
import DOMPurify from 'dompurify';

const ALLOWED_TAGS = ['p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'h1', 'h2', 'h3', 'ul', 'ol', 'li', 'a', 'blockquote'];

export function sanitizeHtml(html: string | null | undefined): string {
  if (!html) return '';
  return DOMPurify.sanitize(html, { ALLOWED_TAGS, ALLOWED_ATTR: ['href', 'title', 'rel', 'target'] });
}

/** Texto plano: un párrafo por bloque, separados por una línea en blanco. */
export function htmlToText(html: string): string {
  const doc = new DOMParser().parseFromString(sanitizeHtml(html), 'text/html');
  const blocks = Array.from(doc.body.querySelectorAll('p, h1, h2, h3, li, blockquote'))
    .filter((el) => !el.querySelector('p, li'))
    .map((el) => (el.tagName === 'LI' ? `- ${el.textContent ?? ''}` : (el.textContent ?? '')).trim())
    .filter(Boolean);
  return (blocks.length ? blocks.join('\n\n') : (doc.body.textContent ?? '')).trim();
}
