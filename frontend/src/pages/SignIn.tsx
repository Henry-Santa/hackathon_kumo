import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function SignIn() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Redirect if already authenticated
    const token = localStorage.getItem('token');
    if (token) {
      navigate('/profile');
    }
  }, [navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch('/api/auth/signin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || 'Sign-in failed');
      }
      const data = await res.json();
      localStorage.setItem('token', data.token);
      navigate('/profile');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ maxWidth: 520 }}>
      <div className="card">
        <h1>Welcome back</h1>
        <div className="muted">Sign in to continue</div>
        <form onSubmit={handleSubmit} className="grid" style={{ gap: 12, marginTop: 12 }}>
          <div className="field">
            <label>Email</label>
            <input
              className="input"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label>Password</label>
            <input
              className="input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div>
            <button className="btn primary" disabled={loading} type="submit">{loading ? 'Signing in…' : 'Sign in'}</button>
          </div>
        </form>
        {error && <p className="muted" style={{ color: 'var(--danger)', marginTop: 8 }}>{error}</p>}
        <p className="muted" style={{ marginTop: 12 }}>No account? <Link to="/signup">Create one</Link></p>
      </div>
    </div>
  );
}


