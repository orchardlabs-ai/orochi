import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  const [email, setEmail] = useState('admin@orochi.local');
  const [password, setPassword] = useState('orochi123');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch {
      setError('Invalid email or password.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-aura" aria-hidden="true" />
      <div className="login-card">
        <div className="login-brand">
          <span className="brand-mark lg" aria-hidden="true">🐉</span>
          <h1>Orochi</h1>
          <p className="login-tagline">HIPAA-conscious clinic voice agent</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>

          {error && <div className="alert alert-error" role="alert">{error}</div>}

          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="creds-hint">
          <span className="creds-label">Seeded credentials</span>
          <code>admin@orochi.local</code>
          <code>orochi123</code>
        </div>
      </div>
    </div>
  );
}
