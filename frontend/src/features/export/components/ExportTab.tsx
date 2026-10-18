/** Pestaña 4: descargar los recursos aprobados para Moodle, Chamilo o como documento, con historial. */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Button, ButtonLink, Card, CardHeader, ConfirmDialog, EmptyState, Spinner } from '@/shared/components/ui';
import { Icon } from '@/shared/components/Icon';
import { saveFile } from '@/shared/lib/saveFile';
import { errorMessage } from '@/shared/api/httpClient';
import { typeInfo } from '@/features/generation/model/resourceCatalog';
import { clearDownloads, exportUnit, listDownloads } from '@/features/export/api/exportApi';
import { FORMATS, formatInfo, resourcesFor } from '@/features/export/model/exportFormats';
import { withStatus } from '@/features/review/model/reviewRules';
import type { Download, DownloadFormat } from '@/shared/types/domain';
import { formatDateTime, plural } from '@/shared/lib/format';
import type { UnitTabProps } from '@/features/units/model/unitTab';

export function ExportTab({ unit, base, resources, resourcesError, reloadResources }: UnitTabProps) {
  const approved = useMemo(() => withStatus(resources ?? [], 'aprobado'), [resources]);
  const [selected, setSelected] = useState<Set<string>>(() => new Set(approved.map((r) => r.id)));
  const [history, setHistory] = useState<Download[] | null>(null);
  const [historyError, setHistoryError] = useState('');
  const [message, setMessage] = useState<{ tone: 'success' | 'warn'; text: string } | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const [clearing, setClearing] = useState(false);

  // Los recursos aprobados después de entrar a la pestaña quedan seleccionados; los que el docente quitó, no.
  const seen = useRef(new Set(approved.map((r) => r.id)));
  const approvedKey = approved.map((r) => r.id).join(',');
  useEffect(() => {
    setSelected((current) => {
      const next = new Set([...current].filter((id) => approved.some((r) => r.id === id)));
      for (const r of approved) if (!current.has(r.id) && !seen.current.has(r.id)) next.add(r.id);
      approved.forEach((r) => seen.current.add(r.id));
      return next;
    });
  }, [approvedKey]);

  useEffect(() => {
    let active = true;
    listDownloads(unit.id)
      .then((list) => active && setHistory(list))
      .catch((e) => active && setHistoryError(errorMessage(e)));
    return () => {
      active = false;
    };
  }, [unit.id]);

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

  const chosen = approved.filter((r) => selected.has(r.id));

  const download = async (format: DownloadFormat) => {
    setMessage(null);
    try {
      const exporting = resourcesFor(format, chosen);
      const { blob, fileName } = await exportUnit(unit.id, format, exporting.map((r) => r.id));
      saveFile(fileName, blob, formatInfo(format).mimeType);
      setMessage({ tone: 'success', text: format === 'documento'
        ? `Se descargó «${fileName}» con ${plural(exporting.length, 'recurso', 'recursos')}.`
        : `Se descargó «${fileName}».` });
      try {
        setHistory(await listDownloads(unit.id));
      } catch (e) {
        setMessage({ tone: 'warn', text: `Se descargó «${fileName}», pero no se pudo actualizar el historial: ${errorMessage(e)}` });
      }
    } catch (e) {
      setMessage({ tone: 'warn', text: errorMessage(e) });
    }
  };

  const clear = async () => {
    setClearing(true);
    try {
      await clearDownloads(unit.id);
      setHistory([]);
      setConfirmClear(false);
    } catch (e) {
      setHistoryError(errorMessage(e));
      setConfirmClear(false);
    } finally {
      setClearing(false);
    }
  };

  if (approved.length === 0)
    return (
      <EmptyState
        icon="export"
        title="Todavía no hay recursos aprobados"
        action={
          <ButtonLink to={`${base}/review`} variant="primary" icon="arrowRight">
            Ir a Revisión
          </ButtonLink>
        }
      >
        Solo se descarga lo que apruebas. Revisa los recursos generados y aprueba los que quieras usar.
      </EmptyState>
    );

  return (
    <div className="stack stack--loose">
      <Card>
        <CardHeader
          title="Recursos aprobados de esta unidad"
          description={`${plural(chosen.length, 'seleccionado', 'seleccionados')} de ${approved.length}`}
          actions={
            chosen.length === approved.length ? (
              <Button compact onClick={() => setSelected(new Set())}>
                Quitar selección
              </Button>
            ) : (
              <Button compact onClick={() => setSelected(new Set(approved.map((r) => r.id)))}>
                Seleccionar todo
              </Button>
            )
          }
        />
        <ul className="select-list">
          {approved.map((r) => (
            <li key={r.id}>
              <label className="check">
                <input
                  type="checkbox"
                  checked={selected.has(r.id)}
                  onChange={(e) =>
                    setSelected((s) => {
                      const next = new Set(s);
                      if (e.target.checked) next.add(r.id);
                      else next.delete(r.id);
                      return next;
                    })
                  }
                />
                <span>
                  <strong>{r.title}</strong>
                  <span className="caption select-list__type">{typeInfo(r.type).singular}</span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      </Card>

      {message && (
        <Alert tone={message.tone} role="status">
          {message.text}
        </Alert>
      )}

      <div className="grid grid--3">
        {FORMATS.map((f) => {
          const count = resourcesFor(f.id, chosen).length;
          return (
            <Card key={f.id} className="format-card">
              <h2 className="title">{f.title}</h2>
              <p className="text-ui">{f.description}</p>
              <p className="format-card__count">
                {f.onlyQuestions ? plural(count, 'pregunta de opción múltiple', 'preguntas de opción múltiple') : plural(count, 'recurso', 'recursos')}
              </p>
              <Button variant="primary" icon="download" disabled={count === 0} onClick={() => void download(f.id)}>
                Descargar .{f.extension}
              </Button>
              <p className="caption">{count === 0 && f.onlyQuestions ? 'Selecciona al menos una pregunta de opción múltiple.' : f.howTo}</p>
            </Card>
          );
        })}
      </div>
      <p className="note">
        <Icon name="info" size={16} />
        Moodle solo importa preguntas de opción múltiple. Chamilo recibe todos los recursos aprobados como páginas de la lección, y el
        documento de la unidad sirve para imprimir o compartir.
      </p>

      <Card>
        <CardHeader
          title="Descargas recientes"
          actions={
            history && history.length > 0 ? (
              <Button compact icon="trash" onClick={() => setConfirmClear(true)}>
                Borrar historial
              </Button>
            ) : undefined
          }
        />
        {historyError && (
          <Alert tone="warn" role="alert">
            {historyError}
          </Alert>
        )}
        {history === null && !historyError ? (
          <Spinner label="Cargando historial…" />
        ) : history && history.length === 0 ? (
          <p className="caption">Todavía no hay descargas de esta unidad.</p>
        ) : (
          history && (
            <div className="table-wrap">
              <table className="table table--stack">
                <thead>
                  <tr>
                    <th scope="col">Fecha</th>
                    <th scope="col">Archivo</th>
                    <th scope="col" className="num">
                      Recursos
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((d) => (
                    <tr key={d.id}>
                      <td data-label="Fecha">{formatDateTime(d.createdAt)}</td>
                      <td data-label="Archivo" className="break">
                        {d.fileName}
                      </td>
                      <td data-label="Recursos" className="num">
                        {d.resourceCount}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </Card>

      <ConfirmDialog
        open={confirmClear}
        title="¿Borrar el historial de descargas?"
        confirmLabel="Borrar historial"
        confirmVariant="danger"
        confirmLoading={clearing}
        onConfirm={() => void clear()}
        onCancel={() => setConfirmClear(false)}
      >
        <p>Se borra la lista de descargas de esta unidad. Los archivos que ya descargaste no se tocan.</p>
      </ConfirmDialog>
    </div>
  );
}
