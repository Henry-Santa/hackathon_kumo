import { useEffect, useState } from 'react';

type Uni = { unitid: number; institution_name: string; state_abbreviation?: string; thumb?: string };

export default function SearchPage() {
  const [q, setQ] = useState('');
  const [results, setResults] = useState<Uni[]>([]);
  const [loading, setLoading] = useState(false);
  const token = localStorage.getItem('token');
  const auth = { Authorization: `Bearer ${token}` } as const;

  const search = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!q.trim()) { setResults([]); return; }
    setLoading(true);
    try {
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
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const action = async (unitid: number, kind: 'likes' | 'dislikes') => {
    try {
      await fetch(`/api/${kind}`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...auth }, body: JSON.stringify({ unitid }) });
      // Remove from results after action
      setResults(prev => prev.filter(u => u.unitid !== unitid));
    } catch (error) {
      console.error('Action failed:', error);
    }
  };

  return (
    <div className="container">
      <div className="title">Search Colleges</div>
      <div className="muted" style={{ fontSize: 16, marginBottom: 32 }}>
        Find and explore colleges that match your interests
      </div>
      
      {/* Search Form */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
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
            🔍
          </div>
          <div>
            <h3 style={{ margin: 0 }}>Search Colleges</h3>
            <div className="muted">Enter a college name to get started</div>
          </div>
        </div>
        
        <form onSubmit={search} style={{ display: 'flex', gap: 12 }}>
          <input 
            className="input" 
            placeholder="Search by college name..." 
            value={q} 
            onChange={(e) => setQ(e.target.value)}
            style={{ flex: 1 }}
          />
          <button 
            className="btn primary" 
            type="submit"
            disabled={loading}
            style={{ padding: '14px 24px' }}
          >
            {loading ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div className="loading-spinner" />
                Searching...
              </span>
            ) : (
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                🔍 Search
              </span>
            )}
          </button>
        </form>
      </div>

      {/* Search Results */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <div style={{ 
            width: 48, 
            height: 48, 
            background: 'linear-gradient(135deg, var(--ok), var(--brand-2))', 
            borderRadius: '50%', 
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 20,
            color: 'white'
          }}>
            🎓
          </div>
          <div>
            <h3 style={{ margin: 0 }}>Search Results</h3>
            <div className="muted">
              {results.length === 0 ? 'No results yet' : `${results.length} college${results.length !== 1 ? 's' : ''} found`}
            </div>
          </div>
        </div>

        {results.length === 0 ? (
          <div style={{ 
            textAlign: 'center', 
            padding: '60px 20px',
            color: 'var(--muted)',
            fontSize: 16
          }}>
            {q.trim() ? (
              <div>
                <div style={{ fontSize: 48, marginBottom: 16 }}>🔍</div>
                <div>No colleges found matching "{q}"</div>
                <div style={{ fontSize: 14, marginTop: 8 }}>Try a different search term</div>
              </div>
            ) : (
              <div>
                <div style={{ fontSize: 48, marginBottom: 16 }}>🎓</div>
                <div>Start searching for colleges above</div>
                <div style={{ fontSize: 14, marginTop: 8 }}>Enter a college name to get started</div>
              </div>
            )}
          </div>
        ) : (
          <div className="grid" style={{ gap: 16 }}>
            {results.map((u) => (
              <div key={u.unitid} className="search-result">
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{ flexShrink: 0 }}>
                    {u.thumb ? (
                      <img 
                        src={u.thumb} 
                        alt="College thumbnail" 
                        style={{ 
                          width: 80, 
                          height: 60, 
                          objectFit: 'cover', 
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border)'
                        }} 
                      />
                    ) : (
                      <div 
                        className="skeleton" 
                        style={{ 
                          width: 80, 
                          height: 60, 
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border)'
                        }} 
                      />
                    )}
                  </div>
                  
                  <div style={{ flex: 1 }}>
                    <h4 style={{ margin: '0 0 4px', fontSize: 16 }}>{u.institution_name}</h4>
                    {u.state_abbreviation && (
                      <div className="muted" style={{ fontSize: 14 }}>
                        📍 {u.state_abbreviation}
                      </div>
                    )}
                  </div>
                  
                  <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                    <button 
                      className="btn ok" 
                      onClick={() => action(u.unitid, 'likes')}
                      style={{ padding: '8px 16px', fontSize: 14 }}
                    >
                      👍 Like
                    </button>
                    <button 
                      className="btn danger" 
                      onClick={() => action(u.unitid, 'dislikes')}
                      style={{ padding: '8px 16px', fontSize: 14 }}
                    >
                      👎 Dislike
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


