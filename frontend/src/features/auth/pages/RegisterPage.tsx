import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { AuthShell } from '@/features/auth/components/AuthShell';
import { Alert, Button, TextField } from '@/shared/components/ui';
import { errorMessage } from '@/shared/api/httpClient';
import { register, registrationProblem } from '@/features/auth/api/authApi';
import { useSession } from '@/app/DataProvider';
import { useSlowNotice } from '@/shared/hooks/useSlowNotice';

export function RegisterPage() {
  const session = useSession();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const slow = useSlowNotice(loading);

  if (session && !loading) return <Navigate to="/courses" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const problem = registrationProblem(name, email, password, confirm);
    if (problem) {
      setError(problem);
      return;
    }
    setLoading(true);
    setError('');
    try {
      await register(name.trim(), email.trim(), password);
      navigate('/courses', { replace: true });
    } catch (err) {
      setError(errorMessage(err));
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Crear cuenta" description="Regístrate para guardar tus cursos, tu material y tus recursos.">
      <form className="stack" onSubmit={submit} noValidate>
        {error && (
          <Alert tone="warn" role="alert">
            {error}
          </Alert>
        )}
        <TextField label="Nombre y apellido" value={name} onChange={setName} autoComplete="name" maxLength={100} />
        <TextField label="Correo electrónico" type="email" value={email} onChange={setEmail} autoComplete="email" maxLength={254} />
        <TextField label="Contraseña" type="password" value={password} onChange={setPassword} autoComplete="new-password" hint="Al menos 8 caracteres." maxLength={200} />
        <TextField label="Repite la contraseña" type="password" value={confirm} onChange={setConfirm} autoComplete="new-password" maxLength={200} />
        <Button type="submit" variant="primary" loading={loading} className="btn--block">
          Crear cuenta
        </Button>
        {slow && (
          <p className="caption" role="status">
            Conectando con el servidor… la primera conexión del día puede tardar hasta un minuto.
          </p>
        )}
      </form>
      <p className="auth__switch">
        ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
      </p>
    </AuthShell>
  );
}
