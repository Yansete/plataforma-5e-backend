/** Pantallas sin sesión (iniciar sesión, crear cuenta): presentación a la izquierda, formulario a la derecha. */
import type { ReactNode } from 'react';

const STEPS = [
  'Sube tu material o busca el tema de la unidad.',
  'Genera recursos que citan de dónde sale cada idea.',
  'Revísalos y descárgalos para Moodle o Chamilo.',
];

export function AuthShell({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <div className="auth">
      <section className="auth__brand" aria-label="Plataforma Docente">
        <div className="auth__brand-text">
          <p className="auth__name">Plataforma Docente</p>
          <p className="auth__tagline">Recursos para tus clases, hechos con tu propio material.</p>
          <ol className="auth__steps">
            {STEPS.map((step, i) => (
              <li key={step}>
                <span className="auth__step-number" aria-hidden="true">
                  {i + 1}
                </span>
                {step}
              </li>
            ))}
          </ol>
        </div>
        <p className="auth__foot">Taller Integrador 1 · 2026-II</p>
      </section>
      <main className="auth__panel" id="contenido">
        <div className="auth__card">
          <h1 data-page-title tabIndex={-1}>
            {title}
          </h1>
          <p className="muted">{description}</p>
          {children}
        </div>
      </main>
    </div>
  );
}
