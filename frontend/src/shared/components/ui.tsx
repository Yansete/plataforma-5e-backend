/**
 * Componentes base del sistema de diseño. Se implementan una sola vez y se reutilizan en todas
 * las pantallas.
 */
import { useEffect, useId, useRef, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Icon, type IconName } from '@/shared/components/Icon';

type ButtonVariant = 'primary' | 'secondary' | 'danger';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  icon?: IconName;
  compact?: boolean;
  loading?: boolean;
}

function buttonClass(variant: ButtonVariant, compact?: boolean, iconOnly?: boolean, extra?: string) {
  return [
    'btn',
    variant === 'primary' && 'btn--primary',
    variant === 'danger' && 'btn--danger',
    compact && 'btn--compact',
    iconOnly && 'btn--icon',
    extra,
  ]
    .filter(Boolean)
    .join(' ');
}

export function Button({ variant = 'secondary', icon, compact, loading, children, className, type = 'button', disabled, ...rest }: ButtonProps) {
  const iconOnly = !children;
  return (
    <button type={type} className={buttonClass(variant, compact, iconOnly, className)} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading ? <span className="spinner" aria-hidden="true" /> : icon && <Icon name={icon} />}
      {children}
    </button>
  );
}

interface ButtonLinkProps {
  to: string;
  variant?: ButtonVariant;
  icon?: IconName;
  children: ReactNode;
  compact?: boolean;
  className?: string;
}

export function ButtonLink({ to, variant = 'secondary', icon, children, compact, className }: ButtonLinkProps) {
  return (
    <Link to={to} className={buttonClass(variant, compact, false, className)}>
      {icon && <Icon name={icon} />}
      {children}
    </Link>
  );
}

export function Card({ children, className, as: Tag = 'section', ...rest }: { children: ReactNode; className?: string; as?: 'section' | 'div' | 'article' | 'aside' } & React.HTMLAttributes<HTMLElement>) {
  return (
    <Tag className={['card', className].filter(Boolean).join(' ')} {...rest}>
      {children}
    </Tag>
  );
}

export function CardHeader({ title, overline, description, actions, headingLevel = 2, id }: { title: ReactNode; overline?: ReactNode; description?: ReactNode; actions?: ReactNode; headingLevel?: 2 | 3; id?: string }) {
  const H = headingLevel === 2 ? 'h2' : 'h3';
  return (
    <div className="card__header">
      <div>
        {overline && <span className="overline">{overline}</span>}
        <H className="title" id={id}>
          {title}
        </H>
        {description && <p className="caption">{description}</p>}
      </div>
      {actions && <div className="btn-row">{actions}</div>}
    </div>
  );
}

export interface Crumb {
  label: string;
  to?: string;
}

/** Ruta de la pantalla: «Mis cursos › RED-301 · Redes › Unidad 1». El último elemento es la pantalla actual. */
export function Breadcrumb({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Ruta" className="breadcrumb">
      <ol>
        {items.map((item, i) => (
          <li key={`${item.label}-${i}`}>
            {item.to && i < items.length - 1 ? <Link to={item.to}>{item.label}</Link> : <span aria-current={i === items.length - 1 ? 'page' : undefined}>{item.label}</span>}
          </li>
        ))}
      </ol>
    </nav>
  );
}

export function PageHeader({ overline, title, description, actions, children }: { overline?: ReactNode; title: string; description?: ReactNode; actions?: ReactNode; children?: ReactNode }) {
  return (
    <header className="page-header">
      <div className="page-header__text">
        {overline && <span className="overline">{overline}</span>}
        <h1 tabIndex={-1} data-page-title>
          {title}
        </h1>
        {description && <p className="muted">{description}</p>}
        {children}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </header>
  );
}

export type TagTone = 'approved' | 'review' | 'discarded' | 'neutral' | 'outline';

export function Tag({ tone = 'neutral', icon, children }: { tone?: TagTone; icon?: IconName; children: ReactNode }) {
  const cls = tone === 'neutral' ? 'tag' : `tag tag--${tone}`;
  return (
    <span className={cls}>
      {icon && <Icon name={icon} size={14} />}
      {children}
    </span>
  );
}

export function Alert({ tone = 'info', title, children, role }: { tone?: 'info' | 'success' | 'warn'; title?: ReactNode; children?: ReactNode; role?: 'status' | 'alert' }) {
  const icon: IconName = tone === 'success' ? 'check' : tone === 'warn' ? 'alert' : 'info';
  return (
    <div className={`alert alert--${tone}`} role={role}>
      <Icon name={icon} />
      <div className="alert__body">
        {title && <span className="alert__title">{title}</span>}
        {children && <div>{children}</div>}
      </div>
    </div>
  );
}

export function EmptyState({ icon = 'info', title, children, action }: { icon?: IconName; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      <span className="empty__icon">
        <Icon name={icon} />
      </span>
      <h3 className="title empty__title">{title}</h3>
      {children && <p className="text-ui">{children}</p>}
      {action}
    </div>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <span className="cluster" role="status">
      <span className="spinner" aria-hidden="true" />
      <span className="text-ui">{label}</span>
    </span>
  );
}

/* ——— Campos de formulario: etiqueta visible siempre asociada ——— */

interface FieldShellProps {
  id: string;
  label: string;
  hint?: ReactNode;
  error?: string;
  children: ReactNode;
  className?: string;
}

export function FieldShell({ id, label, hint, error, children, className }: FieldShellProps) {
  return (
    <div className={['field', className].filter(Boolean).join(' ')}>
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      {hint && (
        <span className="field__hint" id={`${id}-hint`}>
          {hint}
        </span>
      )}
      {children}
      {error && (
        <span className="field__error" id={`${id}-error`}>
          <Icon name="alert" />
          {error}
        </span>
      )}
    </div>
  );
}

function describedBy(id: string, hint?: ReactNode, error?: string) {
  return [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ') || undefined;
}

interface SelectFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string; disabled?: boolean }[];
  hint?: ReactNode;
  error?: string;
  disabled?: boolean;
  className?: string;
  placeholder?: string;
}

export function SelectField({ label, value, onChange, options, hint, error, disabled, className, placeholder }: SelectFieldProps) {
  const id = useId();
  return (
    <FieldShell id={id} label={label} hint={hint} error={error} className={className}>
      <select
        id={id}
        className="select"
        value={value}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, hint, error)}
        onChange={(e) => onChange(e.target.value)}
      >
        {placeholder !== undefined && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((o) => (
          <option key={o.value} value={o.value} disabled={o.disabled}>
            {o.label}
          </option>
        ))}
      </select>
    </FieldShell>
  );
}

interface TextFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  hint?: ReactNode;
  error?: string;
  multiline?: boolean;
  rows?: number;
  className?: string;
  type?: string;
  min?: number;
  max?: number;
  step?: number;
  maxLength?: number;
  autoComplete?: string;
  placeholder?: string;
  disabled?: boolean;
}

export function TextField({ label, value, onChange, hint, error, multiline, rows = 5, className, type = 'text', min, max, step, maxLength, autoComplete, placeholder, disabled }: TextFieldProps) {
  const id = useId();
  const common = {
    id,
    value,
    'aria-invalid': error ? true : undefined,
    'aria-describedby': describedBy(id, hint, error),
    maxLength,
    autoComplete,
    placeholder,
    disabled,
  } as const;
  return (
    <FieldShell id={id} label={label} hint={hint} error={error} className={className}>
      {multiline ? (
        <textarea className="textarea" rows={rows} {...common} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <input className="input" type={type} min={min} max={max} step={step} {...common} onChange={(e) => onChange(e.target.value)} />
      )}
    </FieldShell>
  );
}

export function Checkbox({ label, checked, onChange, hint, describedById, disabled }: { label: ReactNode; checked: boolean; onChange: (checked: boolean) => void; hint?: ReactNode; describedById?: string; disabled?: boolean }) {
  const id = useId();
  return (
    <label className="check" htmlFor={id}>
      <input id={id} type="checkbox" checked={checked} disabled={disabled} aria-describedby={describedById} onChange={(e) => onChange(e.target.checked)} />
      <span>
        {label}
        {hint && <span className="field__hint" style={{ display: 'block' }}>{hint}</span>}
      </span>
    </label>
  );
}

/* ——— Diálogo de confirmación (usa <dialog> nativo: foco atrapado y tecla Esc) ——— */

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  children?: ReactNode;
  confirmLabel: string;
  confirmVariant?: ButtonVariant;
  onConfirm: () => void;
  onCancel: () => void;
  confirmDisabled?: boolean;
  confirmLoading?: boolean;
}

export function ConfirmDialog({ open, title, children, confirmLabel, confirmVariant = 'primary', onConfirm, onCancel, confirmDisabled, confirmLoading }: ConfirmDialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="dialog"
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault();
        onCancel();
      }}
    >
      {open && (
        <div className="dialog__body">
          <h2 className="h2" id={titleId}>
            {title}
          </h2>
          {children}
          <div className="dialog__actions">
            <Button onClick={onCancel}>Cancelar</Button>
            <Button variant={confirmVariant} onClick={onConfirm} disabled={confirmDisabled} loading={confirmLoading}>
              {confirmLabel}
            </Button>
          </div>
        </div>
      )}
    </dialog>
  );
}
