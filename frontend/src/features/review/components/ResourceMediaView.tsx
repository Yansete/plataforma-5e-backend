/** Lo que no es texto en un recurso: gráfico o imagen, audio (con la voz del navegador de respaldo) y actividades. */
import { useEffect, useState } from 'react';
import { Button, Spinner } from '@/shared/components/ui';
import { errorMessage } from '@/shared/api/httpClient';
import { fetchResourceMedia } from '@/features/review/api/reviewApi';
import { formatOf } from '@/features/generation/model/resourceCatalog';
import type { Resource } from '@/shared/types/domain';

function useMediaUrl(resource: Resource, enabled: boolean) {
  const [state, setState] = useState<{ url: string | null; error: string; loading: boolean }>({ url: null, error: '', loading: enabled });
  const version = `${resource.id}|${resource.updatedAt}|${JSON.stringify(resource.structure ?? null)}`;
  useEffect(() => {
    if (!enabled) return;
    let url: string | null = null;
    let cancelled = false;
    setState({ url: null, error: '', loading: true });
    fetchResourceMedia(resource)
      .then((blob) => {
        if (cancelled) return;
        url = URL.createObjectURL(blob);
        setState({ url, error: '', loading: false });
      })
      .catch((error) => !cancelled && setState({ url: null, error: errorMessage(error), loading: false }));
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [version, enabled]);
  return state;
}

function GraphicView({ resource }: { resource: Resource }) {
  const { url, error, loading } = useMediaUrl(resource, true);
  const caption = resource.structure?.caption;
  const note = resource.media?.status === 'fallback' ? resource.media.note : null;
  return (
    <figure className="media-figure">
      {loading && <Spinner label="Cargando la imagen…" />}
      {error && <p className="caption">{error}</p>}
      {url && (
        <>
          <img src={url} alt={resource.structure?.alt || resource.title} />
          <a className="media-figure__open" href={url} target="_blank" rel="noreferrer">
            Ver en tamaño completo
          </a>
        </>
      )}
      {(caption || note) && (
        <figcaption className="caption">
          {caption}
          {note && <span className="media-figure__note">{note}</span>}
        </figcaption>
      )}
    </figure>
  );
}

function AudioView({ resource }: { resource: Resource }) {
  const ready = resource.media?.status === 'ready';
  const { url, error, loading } = useMediaUrl(resource, ready);
  const [speaking, setSpeaking] = useState(false);
  const script = resource.structure?.script ?? resource.body;
  const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window;

  useEffect(() => () => {
    if (canSpeak) window.speechSynthesis.cancel();
  }, [canSpeak]);

  const toggleSpeech = () => {
    if (!canSpeak) return;
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(script);
    utterance.lang = 'es-ES';
    utterance.onend = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
    setSpeaking(true);
  };

  return (
    <div className="media-audio">
      {ready && loading && <Spinner label="Cargando el audio…" />}
      {ready && url && <audio controls preload="metadata" src={url} aria-label={`Audio: ${resource.title}`} />}
      {(!ready || error) && (
        <div className="stack stack--tight">
          <div className="btn-row">
            <Button compact icon={speaking ? 'x' : 'chevronRight'} onClick={toggleSpeech} disabled={!canSpeak}>
              {speaking ? 'Detener' : 'Escuchar con la voz del navegador'}
            </Button>
          </div>
          <p className="caption">{error || resource.media?.note || 'Sin audio generado: el guion se lee con la voz del navegador.'}</p>
        </div>
      )}
      {resource.media?.outdated && <p className="caption">El audio se generó con el guion anterior. Usa «Regenerar» para actualizarlo.</p>}
      <details className="media-audio__script" open={!ready}>
        <summary>Guion del audio</summary>
        <p>{script}</p>
      </details>
    </div>
  );
}

function ActivityPreview({ resource }: { resource: Resource }) {
  const s = resource.structure ?? {};
  if (resource.type === 'emparejamiento')
    return (
      <table className="activity-table">
        <caption className="caption">Pares que el estudiante relaciona (se muestran desordenados)</caption>
        <thead>
          <tr>
            <th scope="col">Término</th>
            <th scope="col">Descripción</th>
          </tr>
        </thead>
        <tbody>
          {(s.pairs ?? []).map((p, i) => (
            <tr key={i}>
              <th scope="row">{p.term}</th>
              <td>{p.definition}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  if (resource.type === 'verdadero_falso')
    return (
      <ol className="activity-list">
        {(s.statements ?? []).map((st, i) => (
          <li key={i}>
            <span>{st.text}</span> <span className={st.isTrue ? 'tag tag--approved' : 'tag tag--discarded'}>{st.isTrue ? 'Verdadero' : 'Falso'}</span>
            {st.feedback && <p className="option__feedback">{st.feedback}</p>}
          </li>
        ))}
      </ol>
    );
  if (resource.type === 'completar_espacios')
    return (
      <ol className="activity-list">
        {(s.blanks ?? []).map((b, i) => (
          <li key={i}>
            {b.sentence} <span className="tag tag--approved">{b.answer}</span>
          </li>
        ))}
      </ol>
    );
  return (
    <div className="stack stack--tight">
      <span className="overline">Orden correcto (el estudiante los recibe desordenados)</span>
      <ol className="activity-list">
        {(s.sequence ?? []).map((step, i) => (
          <li key={i}>{step}</li>
        ))}
      </ol>
    </div>
  );
}

export function ResourceMediaView({ resource }: { resource: Resource }) {
  const format = resource.format ?? formatOf(resource.type);
  if (format === 'text' || !resource.structure) return null;
  if (format === 'interactive') return <ActivityPreview resource={resource} />;
  if (format === 'audio') return <AudioView resource={resource} />;
  return <GraphicView resource={resource} />;
}
