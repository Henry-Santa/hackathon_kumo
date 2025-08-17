import { useEffect, useState } from 'react';

type LikeRow = { UNITID: number; INSTITUTION_NAME: string; CREATED_AT: string };

export default function ProfilePage() {
  const [me, setMe] = useState<any>(null);
  const [likes, setLikes] = useState<LikeRow[]>([]);
  const [dislikes, setDislikes] = useState<LikeRow[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  const token = localStorage.getItem('token');
  const auth = { Authorization: `Bearer ${token}` } as const;

  useEffect(() => {
    if (!token) return;
    Promise.all([
      fetch('/api/me', { headers: auth }).then((r) => r.json()),
      fetch('/api/me/likes', { headers: auth }).then((r) => r.json()),
      fetch('/api/me/dislikes', { headers: auth }).then((r) => r.json()),
    ]).then(([me, l, d]) => {
      setMe(me);
      setLikes(l.items || []);
      setDislikes(d.items || []);
    });
  }, []);

  const update = async (e: React.FormEvent) => {
    e.preventDefault();
    const fd = new FormData(e.target as HTMLFormElement);
    const body = Object.fromEntries(fd.entries());
    await fetch('/api/me', { method: 'PATCH', headers: { 'Content-Type': 'application/json', ...auth }, body: JSON.stringify(body) });
    setMsg('Profile updated successfully!');
    setTimeout(() => setMsg(null), 3000);
  };

  const remove = async (table: 'likes' | 'dislikes', unitid: number) => {
    await fetch(`/api/${table}`, { method: 'DELETE', headers: { 'Content-Type': 'application/json', ...auth }, body: JSON.stringify({ unitid }) });
    // refresh lists
    const [l, d] = await Promise.all([
      fetch('/api/me/likes', { headers: auth }).then((r) => r.json()),
      fetch('/api/me/dislikes', { headers: auth }).then((r) => r.json()),
    ]);
    setLikes(l.items || []);
    setDislikes(d.items || []);
  };

  return (
    <div className="container">
      <div className="title">Your Profile</div>
      <div className="muted" style={{ fontSize: 16, marginBottom: 32 }}>
        Manage your personal information and preferences
      </div>

      {msg && (
        <div className="success-message">
          <span>✅</span>
          {msg}
        </div>
      )}

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        {/* Profile Form */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
            <div style={{ 
              width: 48, 
              height: 48, 
              background: 'linear-gradient(135deg, var(--brand), var(--brand-2))', 
              borderRadius: '50%', 
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 20,
              color: 'white'
            }}>
              👤
            </div>
            <div>
              <h3 style={{ margin: 0 }}>Personal Information</h3>
              <div className="muted">Update your profile details</div>
            </div>
          </div>

          <form onSubmit={update} className="grid" style={{ gap: 20 }}>
            <div className="field">
              <label>📧 Email Address</label>
              <input className="input" name="email" value={me?.email || ''} readOnly />
              <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                Email cannot be changed
              </div>
            </div>
            
            <div className="form-row">
              <div className="field">
                <label>👤 Gender</label>
                <input className="input" name="gender" defaultValue={me?.gender || ''} placeholder="e.g. Male, Female, Nonbinary" />
              </div>
              <div className="field">
                <label>🗺️ State</label>
                <input className="input" name="state_abbreviation" defaultValue={me?.state || ''} placeholder="e.g. CA, NY, TX" />
              </div>
            </div>
            
            <div className="field">
              <label>🌍 Race/Ethnicity</label>
              <input className="input" name="race_ethnicity" defaultValue={me?.race_ethnicity || ''} placeholder="e.g. Asian, Hispanic, White" />
            </div>
            
            <div style={{ 
              background: 'rgba(99, 102, 241, 0.05)', 
              border: '1px solid rgba(99, 102, 241, 0.2)', 
              borderRadius: 'var(--radius-sm)', 
              padding: '20px',
              marginBottom: 20
            }}>
              <h4 style={{ margin: '0 0 16px', color: 'var(--brand)' }}>📊 Test Scores</h4>
              <div className="grid cols-3" style={{ gap: 16 }}>
                <div className="field">
                  <label>📚 SAT ERW</label>
                  <input className="input" name="sat_erw" defaultValue={me?.sat_erw || ''} placeholder="200-800" />
                </div>
                <div className="field">
                  <label>🧮 SAT Math</label>
                  <input className="input" name="sat_math" defaultValue={me?.sat_math || ''} placeholder="200-800" />
                </div>
                <div className="field">
                  <label>📝 ACT</label>
                  <input className="input" name="act_composite" defaultValue={me?.act_composite || ''} placeholder="1-36" />
                </div>
              </div>
            </div>
            
            <div>
              <button className="btn primary" type="submit" style={{ width: '100%' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  💾 Save Changes
                </span>
              </button>
            </div>
          </form>
        </div>

        {/* Preferences */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
            <div style={{ 
              width: 48, 
              height: 48, 
              background: 'linear-gradient(135deg, var(--ok), var(--brand-2-hover))', 
              borderRadius: '50%', 
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 20,
              color: 'white'
            }}>
              ❤️
            </div>
            <div>
              <h3 style={{ margin: 0 }}>Your Preferences</h3>
              <div className="muted">Manage your college preferences</div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 20 }}>
            <div style={{ flex: 1 }}>
              <div style={{ 
                background: 'rgba(16, 185, 129, 0.05)', 
                border: '1px solid rgba(16, 185, 129, 0.2)', 
                borderRadius: 'var(--radius-sm)', 
                padding: '16px',
                marginBottom: 16
              }}>
                <h4 style={{ margin: '0 0 12px', color: 'var(--ok)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  👍 Liked Colleges ({likes.length})
                </h4>
                {likes.length === 0 ? (
                  <div className="muted" style={{ textAlign: 'center', padding: '20px 0' }}>
                    No liked colleges yet
                  </div>
                ) : (
                  <ul style={{ margin: 0, padding: 0 }}>
                    {likes.map((r) => (
                      <li key={r.UNITID} style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center', 
                        padding: '12px 0',
                        borderBottom: '1px solid rgba(16, 185, 129, 0.1)'
                      }}>
                        <span style={{ fontSize: 14 }}>{r.INSTITUTION_NAME}</span>
                        <button 
                          className="btn danger" 
                          onClick={() => remove('likes', r.UNITID)}
                          style={{ padding: '6px 12px', fontSize: 12 }}
                        >
                          Remove
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
            
            <div style={{ flex: 1 }}>
              <div style={{ 
                background: 'rgba(239, 68, 68, 0.05)', 
                border: '1px solid rgba(239, 68, 68, 0.2)', 
                borderRadius: 'var(--radius-sm)', 
                padding: '16px'
              }}>
                <h4 style={{ margin: '0 0 12px', color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  👎 Disliked Colleges ({dislikes.length})
                </h4>
                {dislikes.length === 0 ? (
                  <div className="muted" style={{ textAlign: 'center', padding: '20px 0' }}>
                    No disliked colleges yet
                  </div>
                ) : (
                  <ul style={{ margin: 0, padding: 0 }}>
                    {dislikes.map((r) => (
                      <li key={r.UNITID} style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center', 
                        padding: '12px 0',
                        borderBottom: '1px solid rgba(239, 68, 68, 0.1)'
                      }}>
                        <span style={{ fontSize: 14 }}>{r.INSTITUTION_NAME}</span>
                        <button 
                          className="btn danger" 
                          onClick={() => remove('dislikes', r.UNITID)}
                          style={{ padding: '6px 12px', fontSize: 12 }}
                        >
                          Remove
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


