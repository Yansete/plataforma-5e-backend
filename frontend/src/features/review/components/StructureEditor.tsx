/** Edición de los elementos de un recurso con estructura: conceptos, pasos, pares, afirmaciones, guion… */
import { useState, type FormEvent } from 'react';
import { Alert, Button, Checkbox, TextField } from '@/shared/components/ui';
import { addItem, listItems, moveItem, removeItem, setField, setItem, structureProblem, type StructureSpec } from '@/features/review/model/structureFields';
import type { Resource, ResourceStructure } from '@/shared/types/domain';

interface Props {
  resource: Resource;
  spec: StructureSpec;
  saving: boolean;
  onSave: (structure: ResourceStructure) => Promise<boolean>;
  onCancel: () => void;
}

export function StructureEditor({ resource, spec, saving, onSave, onCancel }: Props) {
  const [structure, setStructure] = useState<ResourceStructure>(resource.structure ?? {});
  const [problem, setProblem] = useState('');
  const items = listItems(structure, spec);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const found = structureProblem(resource.type, structure);
    setProblem(found ?? '');
    if (!found) void onSave(structure);
  };

  return (
    <form className="stack structure-editor" onSubmit={submit} noValidate>
      {spec.fields.map((field) => (
        <TextField
          key={field.key}
          label={field.label}
          multiline={field.kind === 'textarea'}
          rows={field.key === 'script' ? 8 : 3}
          value={String(structure[field.key as keyof ResourceStructure] ?? '')}
          onChange={(v) => setStructure((s) => setField(s, field.key, v))}
          maxLength={field.key === 'script' ? 2400 : 600}
        />
      ))}
      {spec.list && (
        <fieldset className="fieldset">
          <legend className="title">{spec.list.label}</legend>
          <ol className="structure-editor__items">
            {items.map((item, index) => (
              <li key={index} className="structure-editor__item">
                <span className="overline">
                  {spec.list!.item} {index + 1}
                </span>
                {spec.list!.fields === 'string' ? (
                  <TextField label={`${spec.list!.item} ${index + 1}`} multiline rows={2} value={String(item)} onChange={(v) => setStructure((s) => setItem(s, spec, index, null, v))} maxLength={600} />
                ) : (
                  spec.list!.fields.map((field) =>
                    field.kind === 'boolean' ? (
                      <Checkbox
                        key={field.key}
                        label={field.label}
                        checked={Boolean((item as Record<string, unknown>)[field.key])}
                        onChange={(checked) => setStructure((s) => setItem(s, spec, index, field.key, checked))}
                      />
                    ) : (
                      <TextField
                        key={field.key}
                        label={field.label}
                        multiline={field.kind === 'textarea'}
                        rows={2}
                        value={String((item as Record<string, unknown>)[field.key] ?? '')}
                        onChange={(v) => setStructure((s) => setItem(s, spec, index, field.key, v))}
                        maxLength={600}
                      />
                    ),
                  )
                )}
                <div className="btn-row">
                  <Button compact onClick={() => setStructure((s) => moveItem(s, spec, index, -1))} disabled={index === 0} aria-label={`Subir ${spec.list!.item.toLowerCase()} ${index + 1}`}>
                    ↑
                  </Button>
                  <Button compact onClick={() => setStructure((s) => moveItem(s, spec, index, 1))} disabled={index === items.length - 1} aria-label={`Bajar ${spec.list!.item.toLowerCase()} ${index + 1}`}>
                    ↓
                  </Button>
                  <Button compact icon="trash" onClick={() => setStructure((s) => removeItem(s, spec, index))}>
                    Quitar
                  </Button>
                </div>
              </li>
            ))}
          </ol>
          <Button compact icon="plus" onClick={() => setStructure((s) => addItem(s, spec))} disabled={items.length >= 10}>
            Agregar {spec.list.item.toLowerCase()}
          </Button>
        </fieldset>
      )}
      {problem && (
        <Alert tone="warn" role="alert">
          {problem}
        </Alert>
      )}
      <div className="btn-row">
        <Button type="submit" variant="primary" loading={saving}>
          Guardar elementos
        </Button>
        <Button onClick={onCancel}>Cancelar</Button>
      </div>
    </form>
  );
}
