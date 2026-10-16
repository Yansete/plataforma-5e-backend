import { useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AuthShell } from '@/features/auth/components/AuthShell';
import { Alert, Button, TextField } from '@/shared/components/ui';
import { errorMessage } from '@/shared/api/httpClient';
import { login } from '@/features/auth/api/authApi';
import { useSession } from '@/app/DataProvider';
import { useSlowNotice } from '@/shared/hooks/useSlowNotice';

export function LoginPage() {
  const session = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/courses';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const slow = useSlowNotice(loading);

  if (session && !loading) return <Navigate to={from} replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError('Escribe tu correo y tu contraseña.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(errorMessage(err));
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Inicio de sesión" description="Ingresa con tu cuenta de docente.">
      <form className="stack" onSubmit={submit} noValidate>
        {from !== '/courses' && !error && <Alert tone="info">Inicia sesión para continuar.</Alert>}
        {error && (
          <Alert tone="warn" role="alert">
            {error}
          </Alert>
        )}
        <TextField label="Correo electrónico" type="email" value={email} onChange={setEmail} autoComplete="email" />
        <TextField label="Contraseña" type="password" value={password} onChange={setPassword} autoComplete="current-password" />
        <Button type="submit" variant="primary" loading={loading} className="btn--block">
          Iniciar sesión
        </Button>
        {slow && (
          <p className="caption" role="status">
            Conectando con el servidor… la primera conexión del día puede tardar hasta un minuto.
          </p>
        )}
      </form>
      <p className="auth__switch">
        ¿No tienes cuenta? <Link to="/register">Crear cuenta</Link>
      </p>
    </AuthShell>
  );
}
