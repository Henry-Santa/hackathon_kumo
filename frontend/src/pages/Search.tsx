import { useEffect, useState } from 'react';

type Uni = { unitid: number; institution_name: string; state_abbreviation?: string; thumb?: string };

export default function SearchPage() {
  const [q, setQ] = useState('');
  const [results, setResults] = useState<Uni[]>([]);
  const token = localStorage.getItem('token');
  const auth = { Authorization: `Bearer ${token}` } as const;

  const search = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!q.trim()) { setResults([]); return; }
    const r = await fetch(`/api/universities/search?q=${encodeURIComponent(q)}&limit=25`, { headers: auth });
    const j = await r.json();
    const list: Uni[] = j.items || [];
    // Fetch one thumbnail per result in parallel (best-effort)
    const withThumbs = await Promise.all(list.map(async (u) => {
      try {
        const ir = await fetch(`/api/images/by-unitid/${u.unitid}?limit=1`);
        const ij = await ir.json();
        const url = ij?.items?.[0]?.image_url;
        return { ...u, thumb: url };
      } catch {
        return u;
      }
    }));
    setResults(withThumbs);
  };

  const action = async (unitid: number, kind: 'likes' | 'dislikes') => {
    await fetch(`/api/${kind}`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...auth }, body: JSON.stringify({ unitid }) });
  };

  return (
    <div className="container">
      <div className="title">Search colleges</div>
      <form onSubmit={search} style={{ marginTop: 12, display: 'flex', gap: 8 }}>
        <input className="input" placeholder="Search by name" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn" type="submit">Search</button>
      </form>

      <div className="card" style={{ marginTop: 16 }}>
        {results.length === 0 ? <div className="muted">No results</div> : (
          <ul>
            {results.map((u) => (
              <li key={u.unitid} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', gap: 12 }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  {u.thumb ? <img src={u.thumb} alt="thumb" style={{ width: 56, height: 40, objectFit: 'cover', borderRadius: 8 }} /> : <div className="skeleton" style={{ width: 56, height: 40, borderRadius: 8 }} />}
                  <span>{u.institution_name} <span className="muted">{u.state_abbreviation ? `(${u.state_abbreviation})` : ''}</span></span>
                </span>
                <span style={{ display: 'flex', gap: 8 }}>
                  <button className="btn" onClick={() => action(u.unitid, 'likes')}>👍 Like</button>
                  <button className="btn" onClick={() => action(u.unitid, 'dislikes')}>👎 Dislike</button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}


