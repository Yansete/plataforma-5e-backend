/** Pestaña 2: generar recursos con el material de la unidad, eligiendo opciones o escribiendo el pedido. */
import { useMemo, useState, type FormEvent } from 'react';
import { Alert, Button, ButtonLink, Card, EmptyState, SelectField, Spinner, TextField } from '@/shared/components/ui';
import { Icon } from '@/shared/components/Icon';
import { errorMessage } from '@/shared/api/httpClient';
import { DIFFICULTIES, FORMAT_LABELS, GROUPS, RESOURCE_TYPES, countLabel, hasOptions, selectionLabel, typeInfo } from '@/features/generation/model/resourceCatalog';
import { defaultInput, generate, generateMany, type BatchProgress } from '@/features/generation/api/generationApi';
import { materialSummary } from '@/features/materials/api/materialsApi';
import { MAX_REQUEST_LENGTH, interpretRequest, suggestions, type Interpretation } from '@/features/generation/model/requestInterpreter';
import type { GenerationInput, LearningOutcome, MaterialDocument, ResourceType } from '@/shared/types/domain';
import { plural } from '@/shared/lib/format';
import { useSlowNotice } from '@/shared/hooks/useSlowNotice';
import type { UnitTabProps } from '@/features/units/model/unitTab';

type Mode = 'opciones' | 'pedido';

interface LastResult {
  count: number;
  /** «1 pregunta», «6 recursos». */
  label: string;
  usedFallback: boolean;
  failed: { type: ResourceType; message: string }[];
}

function outcomeLabel(o: LearningOutcome): string {
  return `${o.code} · ${o.text.length > 60 ? `${o.text.slice(0, 60).trimEnd()}…` : o.text}`;
}

export function GenerationTab({ unit, base, documents, upsertResources }: UnitTabProps & { documents: MaterialDocument[] }) {
  const material = materialSummary(documents);
  const [mode, setMode] = useState<Mode>('opciones');
  const [input, setInput] = useState<GenerationInput>(() => defaultInput(unit.id));
  const [request, setRequest] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [last, setLast] = useState<LastResult | null>(null);
  const [selected, setSelected] = useState<ResourceType[]>([defaultInput(unit.id).resourceType]);
  const [progress, setProgress] = useState<BatchProgress | null>(null);
  const slow = useSlowNotice(loading, 20000);
  const understood = useMemo(() => interpretRequest(request, unit.outcomes), [request, unit.outcomes]);

  if (material.processed === 0)
    return (
      <EmptyState
        icon="file"
        title="Primero agrega material a la unidad"
        action={
          <ButtonLink to={`${base}/materials`} variant="primary" icon="upload">
            Ir a Material
          </ButtonLink>
        }
      >
        Los recursos se redactan con tu material y citan de dónde sale cada idea. Sube un documento o busca el tema para empezar.
      </EmptyState>
    );

  const run = async (data: GenerationInput) => {
    setLoading(true);
    setError('');
    setLast(null);
    try {
      const result = await generate(data);
      upsertResources(result.resources);
      setLast({ count: result.resources.length, label: countLabel(data.resourceType, result.resources.length), usedFallback: result.usedFallback, failed: [] });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const runMany = async (types: ResourceType[]) => {
    setLoading(true);
    setError('');
    setLast(null);
    try {
      const result = await generateMany(input, types, setProgress);
      upsertResources(result.resources);
      if (result.resources.length === 0) setError(result.failed[0]?.message ?? 'No se generó ningún recurso.');
      else
        setLast({
          count: result.resources.length,
          label: `${result.resources.length} ${result.resources.length === 1 ? 'recurso' : 'recursos'}`,
          usedFallback: result.fallbackTypes.length > 0,
          failed: result.failed,
        });
    } finally {
      setProgress(null);
      setLoading(false);
    }
  };

  const fromRequest = (i: Interpretation): GenerationInput => ({ ...input, ...i, instructions: request.trim().slice(0, MAX_REQUEST_LENGTH) });

  // Los tipos marcados, en el orden de la clase.
  const chosen = RESOURCE_TYPES.filter((t) => selected.includes(t.id)).map((t) => t.id);
  const toggleType = (type: ResourceType, checked: boolean) => {
    setSelected((list) => (checked ? [...list, type] : list.filter((t) => t !== type)));
    setLast(null);
  };

  const submitOptions = (e: FormEvent) => {
    e.preventDefault();
    if (chosen.length === 0) return setError('Marca al menos un tipo de recurso.');
    if (chosen.length === 1) void run({ ...input, resourceType: chosen[0] });
    else void runMany(chosen);
  };

  const submitRequest = (e: FormEvent) => {
    e.preventDefault();
    if (request.trim().length < 5) return setError('Escribe qué necesitas, por ejemplo: «3 preguntas de opción múltiple sobre TCP y UDP».');
    void run(fromRequest(understood));
  };

  const set = <K extends keyof GenerationInput>(key: K, value: GenerationInput[K]) => setInput((i) => ({ ...i, [key]: value }));
  const changeMode = (next: Mode) => {
    setMode(next);
    setLast(null);
    setError('');
  };
  const outcomeOptions = [...unit.outcomes.map((o) => ({ value: o.id, label: outcomeLabel(o) })), { value: '', label: 'Todos los de la unidad' }];

  const feedback = (
    <>
      {error && (
        <Alert tone="warn" title="No se generó contenido" role="alert">
          {error}
        </Alert>
      )}
      {last && last.count > 0 && (
        <Alert tone={last.usedFallback || last.failed.length ? 'warn' : 'success'} title={`Listo: ${last.label} para revisar`} role="status">
          {last.usedFallback
            ? 'La IA no respondió esta vez y se usó el generador de respaldo, que redacta textos más simples. Revísalos con cuidado o vuelve a intentar en unos minutos.'
            : 'Pasa a Revisión para aceptar, editar o descartar lo generado antes de usarlo.'}
          {last.failed.length > 0 && (
            <ul className="caption">
              {last.failed.map((f) => (
                <li key={f.type}>
                  No se generó «{typeInfo(f.type).name}»: {f.message}
                </li>
              ))}
            </ul>
          )}
          <div className="btn-row alert__actions">
            <ButtonLink to={`${base}/review`} variant="primary" compact icon="arrowRight">
              Ir a Revisión
            </ButtonLink>
          </div>
        </Alert>
      )}
    </>
  );

  return (
    <div className="split split--aside">
      <div className="stack">
        <div className="segmented" role="group" aria-label="Forma de pedir">
          <button type="button" aria-pressed={mode === 'opciones'} className="segmented__option" onClick={() => changeMode('opciones')}>
            <Icon name="sliders" />
            Elegir opciones
          </button>
          <button type="button" aria-pressed={mode === 'pedido'} className="segmented__option" onClick={() => changeMode('pedido')}>
            <Icon name="write" />
            Escribir pedido
          </button>
        </div>

        {mode === 'opciones' ? (
          <Card>
            <form className="stack" onSubmit={submitOptions} noValidate>
              <fieldset className="fieldset">
                <legend className="h2">¿Qué quieres generar?</legend>
                <p className="caption">Marca uno o varios recursos en cada momento de la clase; se generan todos juntos.</p>
                <div className="type-groups">
                  {GROUPS.map((group) => (
                    <div key={group} className="type-group" role="group" aria-label={group}>
                      <span className="overline">{group}</span>
                      {RESOURCE_TYPES.filter((t) => t.group === group).map((t) => {
                        const checked = selected.includes(t.id);
                        return (
                          <label key={t.id} className={checked ? 'radio-card radio-card--checked' : 'radio-card'}>
                            <input type="checkbox" name="tipos" value={t.id} checked={checked} onChange={(e) => toggleType(t.id, e.target.checked)} />
                            <span className="radio-card__text">
                              <span>{t.name}</span>
                              {t.format !== 'text' && <span className="format-tag">{FORMAT_LABELS[t.format]}</span>}
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </fieldset>
              {unit.outcomes.length > 0 && (
                <SelectField label="Resultado de aprendizaje" value={input.outcomeId ?? ''} onChange={(v) => set('outcomeId', v || null)} options={outcomeOptions} />
              )}
              <div className="form-grid form-grid--3">
                <SelectField
                  label="Cantidad"
                  value={String(input.quantity)}
                  onChange={(v) => set('quantity', Number(v))}
                  options={[1, 2, 3, 4, 5].map((n) => ({ value: String(n), label: String(n) }))}
                  hint={chosen.length > 1 ? 'De cada tipo marcado.' : undefined}
                />
                <SelectField label="Dificultad" value={input.difficulty} onChange={(v) => set('difficulty', v as GenerationInput['difficulty'])} options={DIFFICULTIES} />
                {chosen.some(hasOptions) && (
                  <SelectField label="Alternativas por pregunta" value={String(input.optionCount)} onChange={(v) => set('optionCount', Number(v))} options={[3, 4, 5].map((n) => ({ value: String(n), label: String(n) }))} />
                )}
              </div>
              <TextField
                label="Indicaciones (opcional)"
                multiline
                rows={3}
                value={input.instructions}
                onChange={(v) => set('instructions', v)}
                maxLength={MAX_REQUEST_LENGTH}
                placeholder="Por ejemplo: plantea situaciones cotidianas, como una videollamada o un juego en línea."
              />
              <details className="more-options">
                <summary>Más opciones: público y competencia</summary>
                <div className="stack">
                  <TextField label="Público" value={input.audience} onChange={(v) => set('audience', v)} maxLength={200} placeholder="Estudiantes de quinto ciclo de Ingeniería de Sistemas" />
                  <TextField label="Competencia" value={input.competency} onChange={(v) => set('competency', v)} maxLength={200} placeholder="Resuelve problemas de conectividad en redes" />
                  <p className="caption">Imágenes, gráficos, audios y actividades interactivas se eligen arriba como tipos de recurso.</p>
                </div>
              </details>
              {feedback}
              <GenerateButton
                loading={loading}
                slow={slow}
                disabled={chosen.length === 0}
                label={chosen.length ? `Generar ${selectionLabel(chosen, input.quantity)}` : 'Marca al menos un recurso'}
                progress={progress ? `Generando ${progress.done + 1} de ${progress.total}: ${typeInfo(progress.current).name}…` : undefined}
              />
            </form>
          </Card>
        ) : (
          <Card>
            <form className="stack" onSubmit={submitRequest} noValidate>
              <TextField
                label="Escribe lo que necesitas"
                multiline
                rows={5}
                value={request}
                onChange={setRequest}
                maxLength={MAX_REQUEST_LENGTH}
                placeholder="Necesito 3 preguntas de opción múltiple para evaluar si mis estudiantes distinguen TCP y UDP, con situaciones como videollamadas y juegos en línea."
                hint={`${request.length}/${MAX_REQUEST_LENGTH} caracteres`}
              />
              <div className="stack stack--tight">
                <span className="overline">Ideas para empezar</span>
                <div className="cluster">
                  {suggestions(unit).map((s) => (
                    <button key={s} type="button" className="chip chip--button" onClick={() => setRequest(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
              {request.trim().length >= 5 && (
                <div className="understood" aria-live="polite">
                  <span className="overline">Así entendí tu pedido</span>
                  <dl className="understood__list">
                    <div>
                      <dt>Qué</dt>
                      <dd>{typeInfo(understood.resourceType).name}</dd>
                    </div>
                    <div>
                      <dt>Cantidad</dt>
                      <dd>{understood.quantity}</dd>
                    </div>
                    <div>
                      <dt>Dificultad</dt>
                      <dd>{DIFFICULTIES.find((d) => d.value === understood.difficulty)?.label}</dd>
                    </div>
                    {hasOptions(understood.resourceType) && (
                      <div>
                        <dt>Alternativas</dt>
                        <dd>{understood.optionCount}</dd>
                      </div>
                    )}
                    <div className="understood__wide">
                      <dt>Resultado</dt>
                      <dd>{understood.outcomeId ? outcomeLabel(unit.outcomes.find((o) => o.id === understood.outcomeId)!) : 'Todos los de la unidad'}</dd>
                    </div>
                  </dl>
                  <p className="caption">Tu texto completo se envía a la IA como indicación.</p>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => {
                      setInput(fromRequest(understood));
                      setSelected([understood.resourceType]);
                      changeMode('opciones');
                    }}
                  >
                    Corregir en «Elegir opciones»
                  </button>
                </div>
              )}
              {feedback}
              <GenerateButton loading={loading} slow={slow} label={`Generar ${countLabel(understood.resourceType, understood.quantity)}`} />
            </form>
          </Card>
        )}
      </div>

      <Card as="aside" className="card--soft how-card" aria-label="Con qué se genera">
        <h2 className="title">Con qué se genera</h2>
        <ul className="how-list">
          <li>
            <Icon name="file" />
            <span>
              <strong>Tu material</strong>
              <span className="caption">
                {plural(material.processed, 'documento', 'documentos')}
              </span>
            </span>
          </li>
          <li>
            <Icon name="write" />
            <span>
              <strong>Redacta la IA</strong>
              <span className="caption">Si no responde, la plataforma usa un generador de respaldo y te avisa.</span>
            </span>
          </li>
          <li>
            <Icon name="quote" />
            <span>
              <strong>Todo con su fuente</strong>
              <span className="caption">Cada afirmación cita tu material. Si el material no alcanza, no se genera.</span>
            </span>
          </li>
        </ul>
      </Card>
    </div>
  );
}

function GenerateButton({ loading, slow, label, disabled, progress }: { loading: boolean; slow: boolean; label: string; disabled?: boolean; progress?: string }) {
  return (
    <div className="stack stack--tight">
      <div className="btn-row">
        <Button type="submit" variant="primary" loading={loading} disabled={disabled}>
          {label}
        </Button>
        {loading && <Spinner label={progress ?? 'Generando…'} />}
      </div>
      <p className="caption">{slow ? 'Sigue trabajando: la IA está redactando con tu material.' : 'Puede tardar hasta un minuto.'}</p>
    </div>
  );
}
