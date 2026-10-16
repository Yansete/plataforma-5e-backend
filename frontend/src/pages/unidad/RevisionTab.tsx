/** Pestaña 3: revisión docente. Cada decisión se guarda en el servidor al momento. */
import { useEffect, useState } from 'react';
import { Alert, Button, ButtonLink, ConfirmDialog, EmptyState, SelectField, Spinner, TextField } from '../../components/ui';
import { Icon } from '../../components/Icon';
import { errorMessage } from '../../services/api';
import { DISCARD_REASONS, discardReasonLabel, typeInfo } from '../../services/catalogo';
import {
  approvalBlockers,
  citedEvidence,
  countByStatus,
  decideOption,
  deleteResource,
  editContent,
  editOption,
  editProblem,
  optionProblem,
  optionSource,
  regenerate,
  saveResource,
  setStatus,
  withStatus,
  highlight,
} from '../../services/revision';
import type { DiscardReason, Evidence, ItemOption, Resource, ReviewStatus, Unit } from '../../types';
import { plural } from '../../utils/format';
import type { UnitTabProps } from './UnidadPage';

const FILTERS: { status: ReviewStatus; label: string }[] = [
  { status: 'pendiente', label: 'Por revisar' },
  { status: 'aprobado', label: 'Aprobados' },
  { status: 'descartado', label: 'Descartados' },
];

const LETTERS = 'ABCDEFGHIJ';

export function RevisionTab({ unit, base, resources, resourcesError, reloadResources, upsertResources, removeResource }: UnitTabProps) {
  const [filter, setFilter] = useState<ReviewStatus>('pendiente');
  const [notice, setNotice] = useState('');

  if (resourcesError)
    return (
      <div className="stack">
        <Alert tone="warn" title="No se pudieron cargar los recursos" role="alert">
          {resourcesError}
        </Alert>
        <div className="btn-row">
          <Button icon="refresh" onClick={() => void reloadResources()}>
            Reintentar
          </Button>
        </div>
      </div>
    );
  if (!resources) return <Spinner label="Cargando recursos…" />;

  const counts = countByStatus(resources);
  const shown = withStatus(resources, filter);

  return (
    <div className="stack stack--loose">
      <div className="filters" role="group" aria-label="Mostrar">
        {FILTERS.map((f) => (
          <button key={f.status} type="button" className="filter" aria-pressed={filter === f.status} onClick={() => setFilter(f.status)}>
            {f.label} ({counts[f.status]})
          </button>
        ))}
      </div>
      {notice && (
        <Alert tone="success" role="status">
          {notice}
        </Alert>
      )}
      {shown.length === 0 ? (
        <EmptyState
          icon="review"
          title={filter === 'pendiente' ? 'No hay recursos por revisar' : filter === 'aprobado' ? 'Todavía no apruebas recursos' : 'No hay recursos descartados'}
          action={
            filter === 'pendiente' && (
              <ButtonLink to={`${base}/generacion`} variant="primary" icon="arrowRight">
                Ir a Generación
              </ButtonLink>
            )
          }
        >
          {filter === 'pendiente'
            ? counts.aprobado > 0
              ? 'Ya revisaste todo. Puedes descargar lo aprobado en Exportación o generar más recursos.'
              : 'Genera recursos con el material de la unidad y aparecerán aquí para que los revises.'
            : filter === 'aprobado'
              ? 'Aprueba un recurso en «Por revisar» para poder descargarlo.'
              : 'Aquí quedan los recursos que descartes, con su motivo.'}
        </EmptyState>
      ) : (
        shown.map((r) => (
          <ResourceReview
            key={r.id}
            resource={r}
            unit={unit}
            onSaved={(saved) => upsertResources([saved])}
            onRemoved={removeResource}
            onRegenerated={(created, replaced) => {
              upsertResources([...created, replaced]);
              setNotice(
                created.length
                  ? 'Se generó una versión nueva y quedó al inicio de «Por revisar». La anterior pasó a «Descartados».'
                  : 'No se pudo redactar una versión nueva con el material disponible.',
              );
            }}
          />
        ))
      )}
    </div>
  );
}

interface ReviewProps {
  resource: Resource;
  unit: Unit;
  onSaved: (resource: Resource) => void;
  onRemoved: (id: string) => void;
  onRegenerated: (created: Resource[], replaced: Resource) => void;
}

function ResourceReview({ resource, unit, onSaved, onRemoved, onRegenerated }: ReviewProps) {
  const [busy, setBusy] = useState<'' | 'guardando' | 'regenerando' | 'borrando'>('');
  const [error, setError] = useState('');
  const [editingContent, setEditingContent] = useState(false);
  const [title, setTitle] = useState(resource.title);
  const [body, setBody] = useState(resource.body);
  const [discarding, setDiscarding] = useState(false);
  const [reason, setReason] = useState<DiscardReason>('sin_sentido');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [focusEvidence, setFocusEvidence] = useState('');

  useEffect(() => {
    setTitle(resource.title);
    setBody(resource.body);
  }, [resource.title, resource.body]);

  const save = async (next: Resource): Promise<boolean> => {
    setBusy('guardando');
    setError('');
    try {
      onSaved(await saveResource(next));
      return true;
    } catch (err) {
      setError(errorMessage(err));
      return false;
    } finally {
      setBusy('');
    }
  };

  const doRegenerate = async () => {
    setBusy('regenerando');
    setError('');
    try {
      const { created, replaced } = await regenerate(resource);
      onRegenerated(created, replaced);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy('');
    }
  };

  const doDelete = async () => {
    setBusy('borrando');
    try {
      await deleteResource(resource);
      setConfirmDelete(false);
      onRemoved(resource.id);
    } catch (err) {
      setError(errorMessage(err));
      setConfirmDelete(false);
      setBusy('');
    }
  };

  const showSource = (evidenceId: string) => {
    setFocusEvidence(evidenceId);
    document.getElementById(`ev-${resource.id}-${evidenceId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const pending = resource.status === 'pendiente';
  const blockers = approvalBlockers(resource);
  const outcome = unit.outcomes.find((o) => o.id === resource.outcomeId);
  const disabled = busy !== '';

  return (
    <div className="review">
      <article className="card review__main" aria-labelledby={`titulo-${resource.id}`}>
        <div className="cluster">
          <span className="tag tag--outline">{[typeInfo(resource.type).singular, outcome?.code].filter(Boolean).join(' · ')}</span>
          {resource.generatorKind && <span className="tag">{resource.generatorKind === 'ia' ? 'Redactado con IA' : 'Generador de respaldo'}</span>}
          <span className="tag">Cita {plural(resource.evidence.length, 'fragmento', 'fragmentos')}</span>
          {resource.edited && <span className="tag">Editado</span>}
          {resource.status === 'aprobado' && <span className="tag tag--approved">Aprobado</span>}
          {resource.status === 'descartado' && <span className="tag tag--discarded">Descartado · {discardReasonLabel(resource.discardReason)}</span>}
        </div>

        {editingContent ? (
          <form
            className="stack"
            onSubmit={(e) => {
              e.preventDefault();
              const problem = editProblem(title, body);
              if (problem) return setError(problem);
              void save(editContent(resource, title.trim(), body.trim())).then((ok) => ok && setEditingContent(false));
            }}
          >
            <TextField label="Título" value={title} onChange={setTitle} maxLength={160} />
            <TextField label={resource.options ? 'Enunciado' : 'Contenido'} multiline rows={8} value={body} onChange={setBody} maxLength={8000} hint="Separa los párrafos con una línea en blanco." />
            <div className="btn-row">
              <Button type="submit" variant="primary" loading={busy === 'guardando'}>
                Guardar cambios
              </Button>
              <Button
                onClick={() => {
                  setEditingContent(false);
                  setTitle(resource.title);
                  setBody(resource.body);
                  setError('');
                }}
              >
                Cancelar
              </Button>
            </div>
          </form>
        ) : (
          <div className="stack stack--tight">
            <div className="review__title-row">
              <h3 className="h2" id={`titulo-${resource.id}`}>
                {resource.title}
              </h3>
              {pending && (
                <Button compact icon="edit" onClick={() => setEditingContent(true)} disabled={disabled}>
                  Editar
                </Button>
              )}
            </div>
            <div className="prose">
              {resource.body
                .split(/\n{2,}/)
                .filter((p) => p.trim())
                .map((p, i) => (
                  <p key={i}>{p}</p>
                ))}
            </div>
          </div>
        )}

        {resource.options && (
          <ol className="options">
            {resource.options.map((o, i) => (
              <OptionRow
                key={o.id}
                option={o}
                letter={LETTERS[i]}
                editable={pending && !disabled}
                source={optionSource(resource, o)}
                onShowSource={showSource}
                onAccept={() => void save(decideOption(resource, o.id, 'aceptado'))}
                onDiscard={(why) => void save(decideOption(resource, o.id, 'descartado', why))}
                onUndo={() => void save(decideOption(resource, o.id, 'pendiente'))}
                onEdit={(text, feedback) => save(editOption(resource, o.id, text, feedback))}
              />
            ))}
          </ol>
        )}

        {error && (
          <Alert tone="warn" role="alert">
            {error}
          </Alert>
        )}

        {pending && (
          <div className="review__actions">
            {blockers.length > 0 && (
              <p className="review__blocker">
                <Icon name="info" size={16} />
                {blockers[0]}
              </p>
            )}
            {discarding ? (
              <div className="inline-form">
                <SelectField label="¿Por qué lo descartas?" value={reason} onChange={(v) => setReason(v as DiscardReason)} options={DISCARD_REASONS} />
                <div className="btn-row">
                  <Button variant="danger" loading={busy === 'guardando'} onClick={() => void save(setStatus(resource, 'descartado', reason)).then((ok) => ok && setDiscarding(false))}>
                    Descartar recurso
                  </Button>
                  <Button onClick={() => setDiscarding(false)}>Cancelar</Button>
                </div>
              </div>
            ) : (
              <div className="btn-row">
                <Button variant="primary" icon="check" disabled={blockers.length > 0 || disabled} loading={busy === 'guardando'} onClick={() => void save(setStatus(resource, 'aprobado'))}>
                  Aprobar recurso
                </Button>
                <Button icon="refresh" loading={busy === 'regenerando'} disabled={disabled} onClick={() => void doRegenerate()}>
                  Regenerar
                </Button>
                <Button icon="x" disabled={disabled} onClick={() => setDiscarding(true)}>
                  Descartar recurso
                </Button>
              </div>
            )}
            {busy === 'regenerando' && <Spinner label="Generando una versión nueva… puede tardar hasta un minuto." />}
          </div>
        )}
        {resource.status === 'aprobado' && (
          <div className="btn-row">
            <Button icon="undo" loading={busy === 'guardando'} onClick={() => void save(setStatus(resource, 'pendiente'))}>
              Volver a revisión
            </Button>
          </div>
        )}
        {resource.status === 'descartado' && (
          <div className="btn-row">
            <Button icon="undo" loading={busy === 'guardando'} disabled={disabled} onClick={() => void save(setStatus(resource, 'pendiente'))}>
              Recuperar
            </Button>
            <Button variant="danger" icon="trash" disabled={disabled} onClick={() => setConfirmDelete(true)}>
              Borrar
            </Button>
          </div>
        )}
      </article>

      <EvidencePanel resource={resource} focused={focusEvidence} />

      <ConfirmDialog
        open={confirmDelete}
        title="¿Borrar este recurso?"
        confirmLabel="Borrar recurso"
        confirmVariant="danger"
        confirmLoading={busy === 'borrando'}
        onConfirm={() => void doDelete()}
        onCancel={() => setConfirmDelete(false)}
      >
        <p>«{resource.title}» se borra de la unidad. No se puede deshacer.</p>
      </ConfirmDialog>
    </div>
  );
}

interface OptionRowProps {
  option: ItemOption;
  letter: string;
  editable: boolean;
  source: Evidence | null;
  onShowSource: (evidenceId: string) => void;
  onAccept: () => void;
  onDiscard: (reason: DiscardReason) => void;
  onUndo: () => void;
  onEdit: (text: string, feedback: string) => Promise<boolean>;
}

function OptionRow({ option: o, letter, editable, source, onShowSource, onAccept, onDiscard, onUndo, onEdit }: OptionRowProps) {
  const [editing, setEditing] = useState(false);
  const [discarding, setDiscarding] = useState(false);
  const [reason, setReason] = useState<DiscardReason>('sin_sentido');
  const [text, setText] = useState(o.text);
  const [feedback, setFeedback] = useState(o.feedback);
  const [problem, setProblem] = useState('');

  const state = o.isCorrect ? 'Respuesta correcta' : o.decision === 'aceptado' ? 'Aceptado' : o.decision === 'descartado' ? `Descartado · ${discardReasonLabel(o.discardReason)}` : 'Sin decidir';
  const tone = o.isCorrect || o.decision === 'aceptado' ? 'tag tag--approved' : o.decision === 'descartado' ? 'tag tag--discarded' : 'tag tag--review';
  const cls = ['option', o.isCorrect && 'option--key', o.decision === 'descartado' && 'option--discarded'].filter(Boolean).join(' ');

  return (
    <li className={cls}>
      <span className="option__letter" aria-hidden="true">
        {letter}
      </span>
      <div className="option__body">
        {editing ? (
          <form
            className="stack stack--tight"
            onSubmit={(e) => {
              e.preventDefault();
              const p = optionProblem(text, feedback);
              setProblem(p ?? '');
              if (!p) void onEdit(text.trim(), feedback.trim()).then((ok) => ok && setEditing(false));
            }}
          >
            <TextField label={`Alternativa ${letter}`} value={text} onChange={setText} maxLength={600} error={problem || undefined} />
            <TextField label="Retroalimentación" multiline rows={2} value={feedback} onChange={setFeedback} maxLength={600} />
            <div className="btn-row">
              <Button type="submit" variant="primary" compact>
                Guardar
              </Button>
              <Button
                compact
                onClick={() => {
                  setEditing(false);
                  setText(o.text);
                  setFeedback(o.feedback);
                  setProblem('');
                }}
              >
                Cancelar
              </Button>
            </div>
          </form>
        ) : (
          <>
            <div className="option__head">
              <span className={o.decision === 'descartado' ? 'option__text option__text--discarded' : 'option__text'}>{o.text}</span>
              <span className={tone}>{state}</span>
              {o.edited && <span className="tag">Editada</span>}
            </div>
            {o.feedback && <p className="option__feedback">{o.feedback}</p>}
            {source && (
              <button type="button" className="link-button" onClick={() => onShowSource(source.id)}>
                Ver origen{source.location ? ` (${source.location})` : ''}
              </button>
            )}
          </>
        )}
        {editable && !editing && !discarding && (
          <div className="option__actions">
            {!o.isCorrect &&
              (o.decision === 'pendiente' ? (
                <>
                  <Button compact icon="check" onClick={onAccept}>
                    Aceptar
                  </Button>
                  <Button compact icon="x" onClick={() => setDiscarding(true)}>
                    Descartar
                  </Button>
                </>
              ) : (
                <Button compact icon="undo" onClick={onUndo}>
                  Deshacer
                </Button>
              ))}
            <Button compact icon="edit" onClick={() => setEditing(true)}>
              Editar
            </Button>
          </div>
        )}
        {discarding && (
          <div className="inline-form">
            <SelectField label="¿Por qué descartas esta alternativa?" value={reason} onChange={(v) => setReason(v as DiscardReason)} options={DISCARD_REASONS} />
            <div className="btn-row">
              <Button
                variant="danger"
                compact
                onClick={() => {
                  setDiscarding(false);
                  onDiscard(reason);
                }}
              >
                Descartar
              </Button>
              <Button compact onClick={() => setDiscarding(false)}>
                Cancelar
              </Button>
            </div>
          </div>
        )}
      </div>
    </li>
  );
}

function EvidencePanel({ resource, focused }: { resource: Resource; focused: string }) {
  const claims = citedEvidence(resource);
  const inClaims = new Set(claims.flatMap((c) => c.evidence.map((e) => e.id)));
  const others = resource.evidence.filter((e) => !inClaims.has(e.id));
  return (
    <aside className="card card--soft review__evidence" aria-label="Evidencia del material">
      <h3 className="title">Evidencia del material</h3>
      <p className="caption">Cada idea del recurso apunta al fragmento de donde salió.</p>
      {claims.length === 0 && others.length === 0 && <p className="caption">Este recurso no tiene fragmentos guardados.</p>}
      {claims.map((c, i) => (
        <div key={i} className="evidence-group">
          <strong className="evidence-group__claim">{c.claim}</strong>
          {c.evidence.map((e) => (
            <EvidenceItem key={e.id} resourceId={resource.id} evidence={e} claim={c.claim} focused={focused === e.id} />
          ))}
        </div>
      ))}
      {others.length > 0 && (
        <div className="evidence-group">
          <strong className="evidence-group__claim">Citado en las alternativas</strong>
          {others.map((e) => (
            <EvidenceItem key={e.id} resourceId={resource.id} evidence={e} claim="" focused={focused === e.id} />
          ))}
        </div>
      )}
    </aside>
  );
}

function EvidenceItem({ resourceId, evidence: e, claim, focused }: { resourceId: string; evidence: Evidence; claim: string; focused: boolean }) {
  const [fullBefore, match, fullAfter] = highlight(e.text, claim);
  // Se muestra la frase citada con un poco de contexto; sin coincidencia, el inicio del fragmento.
  const before = match ? (fullBefore.length > 160 ? `…${fullBefore.slice(-160).trimStart()}` : fullBefore) : '';
  const after = match
    ? fullAfter.length > 160
      ? `${fullAfter.slice(0, 160).trimEnd()}…`
      : fullAfter
    : e.text.length > 360
      ? `${e.text.slice(0, 360).trimEnd()}…`
      : e.text;
  const url = e.sourceUrl && /^https?:\/\//.test(e.sourceUrl) ? e.sourceUrl : null;
  return (
    <blockquote id={`ev-${resourceId}-${e.id}`} className={focused ? 'evidence evidence--focused' : 'evidence'} tabIndex={-1}>
      <p>
        {before}
        {match && <mark>{match}</mark>}
        {after}
      </p>
      <footer className="caption">
        {e.documentName || 'Material de la unidad'}
        {e.location ? ` · ${e.location}` : ''}
        {url && (
          <>
            {' · '}
            <a href={url} target="_blank" rel="noreferrer">
              Ver fuente
            </a>
          </>
        )}
      </footer>
    </blockquote>
  );
}
