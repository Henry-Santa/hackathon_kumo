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
    <div className="container" style={{ maxWidth: 480, display: 'flex', alignItems: 'center', minHeight: 'calc(100vh - 80px)' }}>
      <div className="card" style={{ width: '100%', textAlign: 'center' }}>
        <div style={{ marginBottom: 32 }}>
          <div style={{ 
            width: 80, 
            height: 80, 
            background: 'linear-gradient(135deg, var(--brand), var(--brand-2))', 
            borderRadius: '50%', 
            margin: '0 auto 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 32,
            color: 'white',
            boxShadow: '0 8px 32px rgba(99, 102, 241, 0.3)'
          }}>
            🎓
          </div>
          <h1 style={{ marginBottom: 8 }}>Welcome back!</h1>
          <div className="muted" style={{ fontSize: 16 }}>Sign in to continue your college journey</div>
        </div>
        
        <form onSubmit={handleSubmit} className="grid" style={{ gap: 20, marginBottom: 24 }}>
          <div className="field">
            <label>📧 Email Address</label>
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
            <label>🔒 Password</label>
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
            <button 
              className="btn primary" 
              disabled={loading} 
              type="submit"
              style={{ width: '100%', padding: '16px 24px', fontSize: 16 }}
            >
              {loading ? (
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div className="loading-spinner" />
                  Signing in...
                </span>
              ) : (
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  🚀 Sign In
                </span>
              )}
            </button>
          </div>
        </form>
        
        {error && (
          <div className="error-message">
            <span>⚠️</span>
            {error}
          </div>
        )}
        
        <div style={{ paddingTop: 24, borderTop: '1px solid var(--border)' }}>
          <p className="muted" style={{ margin: 0 }}>
            Don't have an account?{' '}
            <Link to="/signup" style={{ fontWeight: 600, color: 'var(--brand)' }}>
              Create one now
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}


