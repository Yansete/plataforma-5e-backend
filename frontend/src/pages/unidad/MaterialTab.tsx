/** Pestaña 1: material de la unidad. Subir un documento o buscar el tema; ver y borrar lo procesado. */
import { useRef, useState, type DragEvent, type FormEvent } from 'react';
import { Alert, Button, ButtonLink, Card, CardHeader, Checkbox, ConfirmDialog, EmptyState, SelectField, Spinner, TextField } from '../../components/ui';
import { Icon } from '../../components/Icon';
import { errorMessage } from '../../services/api';
import { DOCUMENT_TYPES, MAX_FILE_MB } from '../../services/catalogo';
import { deleteDocument, fileProblem, listFragments, materialSummary, processDocument, searchTopic, uploadAndProcess } from '../../services/material';
import { useData } from '../../state/datos';
import type { Fragment, MaterialDocument } from '../../types';
import { formatBytes, plural } from '../../utils/format';
import type { UnitTabProps } from './UnidadPage';

export function MaterialTab({ unit, base, documents }: UnitTabProps & { documents: MaterialDocument[] }) {
  const summary = materialSummary(documents);
  return (
    <div className="stack stack--loose">
      <div className="grid grid--2">
        <UploadCard unitId={unit.id} outcomes={unit.outcomes} />
        <TopicCard unitId={unit.id} />
      </div>

      <Card>
        <CardHeader title="Material de la unidad" description={`${plural(summary.processed, 'documento', 'documentos')} · ${plural(summary.fragments, 'fragmento', 'fragmentos')}`} />
        {documents.length === 0 ? (
          <EmptyState icon="file" title="Todavía no hay material">
            Sube un documento o busca el tema. Cada idea de los recursos generados citará un fragmento de este material.
          </EmptyState>
        ) : (
          <ul className="doc-list">
            {documents.map((d) => (
              <DocumentRow key={d.id} document={d} outcomeCodes={d.outcomeIds.map((id) => unit.outcomes.find((o) => o.id === id)?.code).filter(Boolean).join(', ')} />
            ))}
          </ul>
        )}
      </Card>

      {summary.processed > 0 && (
        <div className="btn-row btn-row--end">
          <ButtonLink to={`${base}/generacion`} variant="primary" icon="arrowRight">
            Continuar a Generación
          </ButtonLink>
        </div>
      )}
    </div>
  );
}

function UploadCard({ unitId, outcomes }: { unitId: string; outcomes: { id: string; code: string; text: string }[] }) {
  const { reloadDocuments } = useData();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [documentType, setDocumentType] = useState(DOCUMENT_TYPES[0]);
  const [selected, setSelected] = useState<string[]>(() => outcomes.map((o) => o.id));
  const [permission, setPermission] = useState(false);
  const [step, setStep] = useState<'' | 'subiendo' | 'procesando'>('');
  const [error, setError] = useState('');
  const [done, setDone] = useState('');

  const pick = (f: File | undefined | null) => {
    setDone('');
    if (!f) return;
    const problem = fileProblem(f);
    setError(problem ?? '');
    setFile(problem ? null : f);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    pick(e.dataTransfer.files?.[0]);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setDone('');
    if (!file) return setError('Elige un archivo PDF, PPTX o TXT.');
    if (!permission) return setError('Confirma que tienes permiso para usar este material.');
    setError('');
    try {
      const saved = await uploadAndProcess(file, { unitId, outcomeIds: selected, documentType }, setStep);
      await reloadDocuments();
      if (saved.status === 'procesado') setDone(`«${saved.fileName}» quedó listo: ${plural(saved.fragmentCount, 'fragmento', 'fragmentos')}.`);
      else setError(saved.errorMessage ?? 'No se pudo leer el archivo.');
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
    } catch (err) {
      setError(errorMessage(err));
      await reloadDocuments();
    } finally {
      setStep('');
    }
  };

  const busy = step !== '';
  return (
    <Card>
      <form className="stack" onSubmit={submit} noValidate>
        <CardHeader title="Subir documento" />
        <div
          className={dragging ? 'dropzone dropzone--active' : 'dropzone'}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <Icon name="upload" />
          <span className="title">{file ? file.name : 'Arrastra aquí tu archivo'}</span>
          <span className="caption">{file ? formatBytes(file.size) : `PDF, PPTX o TXT · hasta ${MAX_FILE_MB} MB`}</span>
          <input
            ref={inputRef}
            id={`archivo-${unitId}`}
            type="file"
            accept=".pdf,.pptx,.txt"
            className="visually-hidden"
            onChange={(e) => pick(e.target.files?.[0])}
            disabled={busy}
          />
          <label htmlFor={`archivo-${unitId}`} className="btn btn--compact">
            {file ? 'Cambiar archivo' : 'Elegir archivo'}
          </label>
        </div>
        <SelectField label="Tipo de documento" value={documentType} onChange={setDocumentType} options={DOCUMENT_TYPES.map((t) => ({ value: t, label: t }))} disabled={busy} />
        {outcomes.length > 0 && (
          <fieldset className="fieldset">
            <legend className="fieldset__legend">Resultados que trabaja</legend>
            {outcomes.map((o) => (
              <Checkbox
                key={o.id}
                label={
                  <>
                    <strong>{o.code}</strong> {o.text}
                  </>
                }
                checked={selected.includes(o.id)}
                disabled={busy}
                onChange={(checked) => setSelected((list) => (checked ? [...list, o.id] : list.filter((id) => id !== o.id)))}
              />
            ))}
          </fieldset>
        )}
        <Checkbox label="Tengo permiso para usar este material en la plataforma." checked={permission} onChange={setPermission} disabled={busy} />
        {error && (
          <Alert tone="warn" role="alert">
            {error}
          </Alert>
        )}
        {done && (
          <Alert tone="success" role="status">
            {done}
          </Alert>
        )}
        <div className="btn-row">
          <Button type="submit" variant="primary" icon="upload" loading={busy}>
            Subir y procesar
          </Button>
          {busy && <Spinner label={step === 'subiendo' ? 'Subiendo el archivo…' : 'Leyendo el archivo y partiéndolo en fragmentos…'} />}
        </div>
      </form>
    </Card>
  );
}

function TopicCard({ unitId }: { unitId: string }) {
  const { reloadDocuments } = useData();
  const [topic, setTopic] = useState('');
  const [count, setCount] = useState('2');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState('');

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setDone('');
    if (topic.trim().length < 3) return setError('Escribe un tema de al menos 3 caracteres.');
    setError('');
    setLoading(true);
    try {
      const found = await searchTopic(unitId, topic, Number(count));
      await reloadDocuments();
      setDone(`Se agregaron ${plural(found.length, 'documento', 'documentos')} sobre «${topic.trim()}». Revisa lo que trajo antes de generar.`);
      setTopic('');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <form className="stack" onSubmit={submit} noValidate>
        <CardHeader
          title="Buscar el tema"
          description="¿No tienes material? Escribe el tema y la plataforma busca información para procesarla igual que un documento. Revisa lo que trae: tu propio material sigue siendo la mejor evidencia."
        />
        <TextField label="Tema" value={topic} onChange={setTopic} maxLength={120} placeholder="Protocolo de control de transmisión" disabled={loading} />
        <SelectField label="Documentos a traer" value={count} onChange={setCount} options={['1', '2', '3'].map((v) => ({ value: v, label: v }))} disabled={loading} />
        {error && (
          <Alert tone="warn" role="alert">
            {error}
          </Alert>
        )}
        {done && (
          <Alert tone="success" role="status">
            {done}
          </Alert>
        )}
        <div className="btn-row">
          <Button type="submit" variant="primary" icon="search" loading={loading}>
            Buscar y procesar
          </Button>
          {loading && <Spinner label="Buscando y procesando…" />}
        </div>
        <p className="caption">Cada documento encontrado se guarda con su enlace de origen.</p>
      </form>
    </Card>
  );
}

const SHOWN_FRAGMENTS = 3;

function DocumentRow({ document: d, outcomeCodes }: { document: MaterialDocument; outcomeCodes: string }) {
  const { reloadDocuments } = useData();
  const [fragments, setFragments] = useState<Fragment[] | null>(null);
  const [open, setOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);

  const toggle = async () => {
    if (open) return setOpen(false);
    setOpen(true);
    if (fragments) return;
    try {
      setFragments(await listFragments(d.id));
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const retry = async () => {
    setBusy(true);
    setError('');
    try {
      await processDocument(d.id);
      await reloadDocuments();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    try {
      await deleteDocument(d.id);
      setConfirmDelete(false);
      await reloadDocuments();
    } catch (err) {
      setError(errorMessage(err));
      setConfirmDelete(false);
      setBusy(false);
    }
  };

  const fromTopic = Boolean(d.origin);
  const sourceUrl = d.origin?.url && /^https?:\/\//.test(d.origin.url) ? d.origin.url : null;
  const shown = fragments ? (showAll ? fragments : fragments.slice(0, SHOWN_FRAGMENTS)) : [];
  return (
    <li className="doc">
      <div className="doc__row">
        <span className="doc__icon" aria-hidden="true">
          <Icon name={fromTopic ? 'search' : 'file'} />
        </span>
        <div className="doc__info">
          <span className="doc__name">{fromTopic ? d.origin?.tema || d.fileName.replace(/\.txt$/, '') : d.fileName}</span>
          <span className="caption">
            {fromTopic ? (
              <>
                Encontrado por tema
                {sourceUrl && (
                  <>
                    {' · '}
                    <a href={sourceUrl} target="_blank" rel="noreferrer">
                      Ver fuente
                    </a>
                  </>
                )}
              </>
            ) : (
              [d.documentType, outcomeCodes].filter(Boolean).join(' · ')
            )}
          </span>
          <span className={d.status === 'procesado' ? 'doc__status doc__status--ok' : d.status === 'error' ? 'doc__status doc__status--error' : 'doc__status'}>
            {d.status === 'procesado'
              ? `Procesado · ${plural(d.fragmentCount, 'fragmento', 'fragmentos')}`
              : d.status === 'error'
                ? `No se pudo procesar${d.errorMessage ? `: ${d.errorMessage}` : ''}`
                : 'Sin procesar'}
          </span>
        </div>
        <div className="btn-row">
          {d.status === 'procesado' ? (
            <Button compact onClick={() => void toggle()} aria-expanded={open}>
              {open ? 'Ocultar fragmentos' : 'Ver fragmentos'}
            </Button>
          ) : (
            <Button compact icon="refresh" loading={busy} onClick={() => void retry()}>
              Procesar de nuevo
            </Button>
          )}
          <Button compact icon="trash" aria-label={`Borrar ${d.fileName}`} onClick={() => setConfirmDelete(true)} disabled={busy} />
        </div>
      </div>
      {error && (
        <Alert tone="warn" role="alert">
          {error}
        </Alert>
      )}
      {open && (
        <div className="fragments">
          {!fragments && !error && <Spinner label="Cargando fragmentos…" />}
          {shown.map((f) => (
            <blockquote key={f.id} className="fragment">
              <span className="caption">
                Fragmento {f.orden + 1} · {f.location}
              </span>
              <p>{f.text.length > 320 ? `${f.text.slice(0, 320).trimEnd()}…` : f.text}</p>
            </blockquote>
          ))}
          {fragments && fragments.length > SHOWN_FRAGMENTS && (
            <button type="button" className="link-button" onClick={() => setShowAll((v) => !v)}>
              {showAll ? 'Ver menos' : `y ${plural(fragments.length - SHOWN_FRAGMENTS, 'fragmento más', 'fragmentos más')}`}
            </button>
          )}
        </div>
      )}
      <ConfirmDialog
        open={confirmDelete}
        title="¿Borrar este documento?"
        confirmLabel="Borrar documento"
        confirmVariant="danger"
        confirmLoading={busy}
        onConfirm={() => void remove()}
        onCancel={() => setConfirmDelete(false)}
      >
        <p>
          Se borra «{d.fileName}» con sus fragmentos. Los recursos ya generados conservan su evidencia, pero no podrás generar nuevos con este
          material.
        </p>
      </ConfirmDialog>
    </li>
  );
}
