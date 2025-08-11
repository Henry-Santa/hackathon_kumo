import { useState } from 'react';
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

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
      navigate('/');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 520, margin: '64px auto', fontFamily: 'Inter, system-ui, Arial' }}>
      <h1>Create account</h1>
      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 12 }}>
        <input name="email" type="email" placeholder="Email" value={form.email} onChange={handleChange} required />
        <input name="password" type="password" placeholder="Password" value={form.password} onChange={handleChange} required />

        <select name="gender" value={form.gender} onChange={handleChange}>
          <option value="">Gender (optional)</option>
          <option>Male</option>
          <option>Female</option>
          <option>Nonbinary</option>
          <option>Prefer not to say</option>
        </select>

        <select name="state" value={form.state} onChange={handleChange}>
          <option value="">State/Territory (optional)</option>
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
        <select name="race" value={form.race} onChange={handleChange}>
          <option value="">Race/Ethnicity (optional)</option>
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

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
          <input name="satErw" placeholder="SAT ERW" value={form.satErw} onChange={handleChange} />
          <input name="satMath" placeholder="SAT Math" value={form.satMath} onChange={handleChange} />
          <input name="act" placeholder="ACT" value={form.act} onChange={handleChange} />
        </div>

        <button disabled={loading} type="submit">{loading ? 'Creating...' : 'Create account'}</button>
      </form>
      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      <p style={{ marginTop: 12 }}>Have an account? <Link to="/">Sign in</Link></p>
    </div>
  );
}


