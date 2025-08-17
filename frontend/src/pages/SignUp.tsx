import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function SignUp() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: '',
    password: '',
    gender: '',
    state: '',
    race: '',
    satErw: '',
    satMath: '',
    act: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0);

  const steps = useMemo(() => [
    { key: 'account', title: 'Create your account', subtitle: 'Secure your login to personalize recommendations.', icon: '🔐' },
    { key: 'about', title: 'About you', subtitle: 'Optional demographics help us tailor insights.', icon: '👤' },
    { key: 'sat_erw', title: 'SAT — Evidence-Based Reading & Writing', subtitle: 'Optional. Enter if you have a score.', icon: '📚' },
    { key: 'sat_math', title: 'SAT — Math', subtitle: 'Optional. Enter if you have a score.', icon: '🧮' },
    { key: 'act', title: 'ACT — Composite', subtitle: 'Optional. Enter if you have a score.', icon: '📝' },
  ], []);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) navigate('/profile');
  }, [navigate]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  };

  const validateStep = (s: number): string | null => {
    if (s === 0) {
      if (!form.email.trim()) return 'Email is required';
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) return 'Enter a valid email';
      if (!form.password || form.password.length < 6) return 'Password must be at least 6 characters';
    }
    if (s === 2 && form.satErw.trim()) {
      const v = Number(form.satErw);
      if (!Number.isFinite(v) || v < 200 || v > 800) return 'SAT ERW must be between 200 and 800';
    }
    if (s === 3 && form.satMath.trim()) {
      const v = Number(form.satMath);
      if (!Number.isFinite(v) || v < 200 || v > 800) return 'SAT Math must be between 200 and 800';
    }
    if (s === 4 && form.act.trim()) {
      const v = Number(form.act);
      if (!Number.isFinite(v) || v < 1 || v > 36) return 'ACT must be between 1 and 36';
    }
    return null;
  };

  const submit = async () => {
    setError(null);
    setLoading(true);
    try {
      const payload = {
        email: form.email,
        password: form.password,
        gender: form.gender || null,
        state_abbreviation: form.state || null,
        race_ethnicity: form.race || null,
        sat_erw: form.satErw ? Number(form.satErw) : null,
        sat_math: form.satMath ? Number(form.satMath) : null,
        act_composite: form.act ? Number(form.act) : null,
      };
      const res = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || 'Sign-up failed');
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

  const next = async () => {
    const err = validateStep(step);
    if (err) { setError(err); return; }
    setError(null);
    if (step < steps.length - 1) setStep((s) => s + 1);
    else await submit();
  };

  const back = () => {
    setError(null);
    setStep((s) => Math.max(0, s - 1));
  };

  const skip = () => {
    // About + test scores are optional
    if (step === 0) return; // cannot skip account
    setError(null);
    if (step < steps.length - 1) setStep((s) => s + 1);
    else submit();
  };

  const progress = ((step + 1) / steps.length) * 100;

  return (
    <div className="container" style={{ maxWidth: 720, display: 'flex', alignItems: 'center', minHeight: 'calc(100vh - 80px)' }}>
      <div className="card" style={{ width: '100%' }}>
        {/* Header with progress */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
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
            {steps[step].icon}
          </div>
          <h1 style={{ marginBottom: 8 }}>{steps[step].title}</h1>
          <div className="muted" style={{ fontSize: 16, marginBottom: 24 }}>{steps[step].subtitle}</div>
          
          {/* Progress indicator */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, marginBottom: 24 }}>
            <div className="muted" style={{ fontSize: 14 }}>Step {step + 1} of {steps.length}</div>
            <div className="progress" style={{ width: 200, height: 8 }}>
              <div className="bar" style={{ width: `${progress}%` }} />
            </div>
          </div>
        </div>

        {/* Step content */}
        <div style={{ position: 'relative', overflow: 'hidden', marginBottom: 32 }}>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${steps.length}, 100%)`,
              transition: 'transform 380ms cubic-bezier(0.22, 1, 0.36, 1)',
              transform: `translateX(-${step * 100}%)`,
            }}
          >
            {/* Step 1: Account */}
            <div style={{ paddingRight: 8 }}>
              <div className="grid" style={{ gap: 20 }}>
                <div className="form-row">
                  <div className="field">
                    <label>📧 Email Address</label>
                    <input
                      className="input"
                      name="email"
                      type="email"
                      placeholder="you@example.com"
                      value={form.email}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="field">
                    <label>🔒 Password</label>
                    <input
                      className="input"
                      name="password"
                      type="password"
                      placeholder="••••••••"
                      value={form.password}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Step 2: About you (optional) */}
            <div style={{ paddingRight: 8 }}>
              <div className="grid cols-3" style={{ gap: 20 }}>
                <div className="field">
                  <label>👤 Gender (optional)</label>
                  <select className="select" name="gender" value={form.gender} onChange={handleChange}>
                    <option value="">Select…</option>
                    <option>Male</option>
                    <option>Female</option>
                    <option>Nonbinary</option>
                    <option>Prefer not to say</option>
                  </select>
                </div>
                <div className="field">
                  <label>🗺️ State/Territory (optional)</label>
                  <select className="select" name="state" value={form.state} onChange={handleChange}>
                    <option value="">Select…</option>
                    <option>Alabama</option>
                    <option>Alaska</option>
                    <option>Arizona</option>
                    <option>Arkansas</option>
                    <option>California</option>
                    <option>Colorado</option>
                    <option>Connecticut</option>
                    <option>Delaware</option>
                    <option>District of Columbia</option>
                    <option>Florida</option>
                    <option>Georgia</option>
                    <option>Hawaii</option>
                    <option>Idaho</option>
                    <option>Illinois</option>
                    <option>Indiana</option>
                    <option>Iowa</option>
                    <option>Kansas</option>
                    <option>Kentucky</option>
                    <option>Louisiana</option>
                    <option>Maine</option>
                    <option>Maryland</option>
                    <option>Massachusetts</option>
                    <option>Michigan</option>
                    <option>Minnesota</option>
                    <option>Mississippi</option>
                    <option>Missouri</option>
                    <option>Montana</option>
                    <option>Nebraska</option>
                    <option>Nevada</option>
                    <option>New Hampshire</option>
                    <option>New Jersey</option>
                    <option>New Mexico</option>
                    <option>New York</option>
                    <option>North Carolina</option>
                    <option>North Dakota</option>
                    <option>Ohio</option>
                    <option>Oklahoma</option>
                    <option>Oregon</option>
                    <option>Pennsylvania</option>
                    <option>Rhode Island</option>
                    <option>South Carolina</option>
                    <option>South Dakota</option>
                    <option>Tennessee</option>
                    <option>Texas</option>
                    <option>Utah</option>
                    <option>Vermont</option>
                    <option>Virginia</option>
                    <option>Washington</option>
                    <option>West Virginia</option>
                    <option>Wisconsin</option>
                    <option>Wyoming</option>
                    <option>American Samoa</option>
                    <option>Guam</option>
                    <option>Northern Mariana Islands</option>
                    <option>Puerto Rico</option>
                    <option>U.S. Virgin Islands</option>
                  </select>
                </div>
                <div className="field">
                  <label>🌍 Race/Ethnicity (optional)</label>
                  <select className="select" name="race" value={form.race} onChange={handleChange}>
                    <option value="">Select…</option>
                    <option>American Indian or Alaska Native</option>
                    <option>Asian</option>
                    <option>Black or African American</option>
                    <option>Hispanic/Latino</option>
                    <option>Native Hawaiian or Other Pacific Islander</option>
                    <option>White</option>
                    <option>Two or more races</option>
                    <option>Unknown</option>
                    <option>Nonresident</option>
                    <option>Other</option>
                    <option>Prefer not to say</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Step 3: SAT ERW (optional) */}
            <div style={{ paddingRight: 8 }}>
              <div className="grid" style={{ gap: 20 }}>
                <div className="field">
                  <label>📚 SAT Evidence-Based Reading & Writing</label>
                  <input
                    className="input"
                    name="satErw"
                    inputMode="numeric"
                    placeholder="e.g. 650"
                    value={form.satErw}
                    onChange={handleChange}
                  />
                  <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                    Score range: 200-800
                  </div>
                </div>
              </div>
            </div>

            {/* Step 4: SAT Math (optional) */}
            <div style={{ paddingRight: 8 }}>
              <div className="grid" style={{ gap: 20 }}>
                <div className="field">
                  <label>🧮 SAT Math</label>
                  <input
                    className="input"
                    name="satMath"
                    inputMode="numeric"
                    placeholder="e.g. 680"
                    value={form.satMath}
                    onChange={handleChange}
                  />
                  <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                    Score range: 200-800
                  </div>
                </div>
              </div>
            </div>

            {/* Step 5: ACT (optional) */}
            <div style={{ paddingRight: 8 }}>
              <div className="grid" style={{ gap: 20 }}>
                <div className="field">
                  <label>📝 ACT Composite</label>
                  <input
                    className="input"
                    name="act"
                    inputMode="numeric"
                    placeholder="e.g. 30"
                    value={form.act}
                    onChange={handleChange}
                  />
                  <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                    Score range: 1-36
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation buttons */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn" onClick={back} disabled={step === 0 || loading}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                ← Back
              </span>
            </button>
            {step > 0 && step < steps.length && (
              <button className="btn" onClick={skip} disabled={loading}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  ⏭️ Skip
                </span>
              </button>
            )}
          </div>
          <div>
            <button className="btn primary" onClick={next} disabled={loading}>
              {step === steps.length - 1 ? (
                loading ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div className="loading-spinner" />
                    Creating...
                  </span>
                ) : (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    ✨ Create Account
                  </span>
                )
              ) : (
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  Next →
                </span>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="error-message">
            <span>⚠️</span>
            {error}
          </div>
        )}
        
        <div style={{ paddingTop: 24, borderTop: '1px solid var(--border)', textAlign: 'center' }}>
          <p className="muted" style={{ margin: 0 }}>
            Already have an account?{' '}
            <Link to="/" style={{ fontWeight: 600, color: 'var(--brand)' }}>
              Sign in here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}


