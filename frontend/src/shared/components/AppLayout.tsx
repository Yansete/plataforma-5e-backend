/**
 * Marco de las pantallas con sesión: menú lateral (cursos y unidades), barra para celular y contenido.
 */
import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useMatch, useNavigate } from 'react-router-dom';
import { logout } from '@/features/auth/api/authApi';
import { useData, useSession } from '@/app/DataProvider';
import { ErrorBoundary } from '@/shared/components/ErrorBoundary';
import { Icon } from '@/shared/components/Icon';

export function AppLayout() {
  const session = useSession();
  const { courses } = useData();
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const firstRender = useRef(true);

  // Las pestañas de una unidad son la misma pantalla: cambiar de pestaña no la reinicia.
  const pageKey = location.pathname.replace(/\/(materials|generation|review|export)\/?$/, '');
  const match = useMatch('/courses/:courseId/*');
  const courseId = match?.params.courseId;
  const course = courseId && courseId !== 'new' ? courses?.find((c) => c.id === courseId) : undefined;

  // Al cambiar de pantalla, el foco va al título (salvo en la carga inicial).
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    document.querySelector<HTMLElement>('[data-page-title]')?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }, [pageKey]);

  useEffect(() => setMenuOpen(false), [location.pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    closeButtonRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [menuOpen]);

  const signOut = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <>
      <a className="skip-link" href="#contenido">
        Saltar al contenido
      </a>
      <div className="app">
        <div className="mobile-bar">
          <Link to="/courses" className="mobile-bar__title">
            Plataforma Docente
          </Link>
          <button ref={menuButtonRef} type="button" className="mobile-bar__menu" aria-expanded={menuOpen} aria-controls="navegacion" onClick={() => setMenuOpen(true)}>
            <Icon name="menu" />
            Menú
          </button>
        </div>

        {menuOpen && <div className="sidebar-backdrop" onClick={() => setMenuOpen(false)} aria-hidden="true" />}

        <nav id="navegacion" className={menuOpen ? 'sidebar sidebar--open' : 'sidebar'} aria-label="Navegación principal">
          <button
            ref={closeButtonRef}
            type="button"
            className="sidebar-close"
            aria-label="Cerrar menú"
            onClick={() => {
              setMenuOpen(false);
              menuButtonRef.current?.focus();
            }}
          >
            <Icon name="x" />
          </button>
          <Link to="/courses" className="sidebar__brand">
            Plataforma Docente
          </Link>

          <ul className="nav-list">
            <li>
              <NavLink to="/courses" end className="nav-link">
                <Icon name="book" />
                <span>Mis cursos</span>
              </NavLink>
            </li>
          </ul>

          {course && (
            <div className="nav-group">
              <p className="sidebar__section-label">Curso</p>
              <NavLink to={`/courses/${course.id}`} end className="nav-link nav-link--strong">
                <span>
                  {course.code} · {course.name}
                </span>
              </NavLink>
              {course.units.length > 0 && <p className="sidebar__section-label">Unidades</p>}
              <ul className="nav-list">
                {course.units.map((u) => (
                  <li key={u.id}>
                    <NavLink to={`/courses/${course.id}/units/${u.id}`} className="nav-link">
                      <span>
                        {u.number} · {u.title}
                      </span>
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="sidebar__footer">
            {session && (
              <span className="sidebar__user">
                <strong>{session.name}</strong>
                <span>{session.email}</span>
              </span>
            )}
            <button type="button" className="sidebar__logout" onClick={() => void signOut()}>
              <Icon name="logout" />
              Cerrar sesión
            </button>
          </div>
        </nav>

        <main className="main" id="contenido" tabIndex={-1}>
          <div className="content">
            <ErrorBoundary key={pageKey}>
              <Outlet />
            </ErrorBoundary>
          </div>
        </main>
      </div>
    </>
  );
}
