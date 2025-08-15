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
    setMsg('Saved');
    setTimeout(() => setMsg(null), 1500);
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
      <div className="title">Your profile</div>
      {msg && <div className="muted">{msg}</div>}

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <div className="card">
          <form onSubmit={update} className="grid" style={{ gap: 10 }}>
            <div className="field">
              <label>Email</label>
              <input className="input" name="email" value={me?.email || ''} readOnly />
            </div>
            <div className="field">
              <label>Gender</label>
              <input className="input" name="gender" defaultValue={me?.gender || ''} />
            </div>
            <div className="field">
              <label>State</label>
              <input className="input" name="state_abbreviation" defaultValue={me?.state || ''} />
            </div>
            <div className="field">
              <label>Race/ethnicity</label>
              <input className="input" name="race_ethnicity" defaultValue={me?.race_ethnicity || ''} />
            </div>
            <div className="grid cols-3">
              <div className="field"><label>SAT ERW</label><input className="input" name="sat_erw" defaultValue={me?.sat_erw || ''} /></div>
              <div className="field"><label>SAT Math</label><input className="input" name="sat_math" defaultValue={me?.sat_math || ''} /></div>
              <div className="field"><label>ACT</label><input className="input" name="act_composite" defaultValue={me?.act_composite || ''} /></div>
            </div>
            <div>
              <button className="btn primary" type="submit">Save</button>
            </div>
          </form>
        </div>

        <div className="card">
          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ flex: 1 }}>
              <h3>Likes</h3>
              <ul>
                {likes.map((r) => (
                  <li key={r.UNITID} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0' }}>
                    <span>{r.INSTITUTION_NAME}</span>
                    <button className="btn danger" onClick={() => remove('likes', r.UNITID)}>Remove</button>
                  </li>
                ))}
              </ul>
            </div>
            <div style={{ flex: 1 }}>
              <h3>Dislikes</h3>
              <ul>
                {dislikes.map((r) => (
                  <li key={r.UNITID} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0' }}>
                    <span>{r.INSTITUTION_NAME}</span>
                    <button className="btn danger" onClick={() => remove('dislikes', r.UNITID)}>Remove</button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


