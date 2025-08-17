import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import TwoCol from '../components/TwoCol';

type ImageItem = { image_url: string };
type University = {
  unitid: number;
  institution_name: string;
  city_location_of_institution?: string;
  state_abbreviation?: string;
  institutions_internet_website_address?: string;
  percent_admitted_total?: number;
  admissions_yield_total?: number;
  tuition_and_fees_2023_24?: number;
  total_price_for_in_state_students_living_on_campus_2023_24?: number;
  total_price_for_out_of_state_students_living_on_campus_2023_24?: number;
  institution_size_category?: string;
  level_of_institution?: string;
  control_of_institution?: string;
  degree_of_urbanization_urban_centric_locale?: string;
  percent_of_undergraduate_enrollment_that_are_women?: number;
  full_time_retention_rate_2023?: number;
  student_to_faculty_ratio?: number;
  graduation_rate_total_cohort?: number;
  percent_of_full_time_first_time_undergraduates_awarded_any_financial_aid?: number;
  average_amount_of_federal_state_local_or_institutional_grant_aid_awarded?: number;
  average_net_price_students_awarded_grant_or_scholarship_aid_2022_23?: number;
  applicants_total?: number;
  percent_of_first_time_degree_certificate_seeking_students_submitting_sat_scores?: number;
  percent_of_first_time_degree_certificate_seeking_students_submitting_act_scores?: number;
  sat_evidence_based_reading_and_writing_25th_percentile_score?: number;
  sat_evidence_based_reading_and_writing_50th_percentile_score?: number;
  sat_evidence_based_reading_and_writing_75th_percentile_score?: number;
  sat_math_25th_percentile_score?: number;
  sat_math_50th_percentile_score?: number;
  sat_math_75th_percentile_score?: number;
  act_composite_25th_percentile_score?: number;
  act_composite_50th_percentile_score?: number;
  act_composite_75th_percentile_score?: number;
  images?: Array<{ image_url: string }>;
};

type Me = {
  user_id: string;
  email?: string;
  sat_erw?: number;
  sat_math?: number;
  act_composite?: number;
};

export default function UniversityProfile() {
  const [me, setMe] = useState<Me | null>(null);
  const [uni, setUni] = useState<University | null>(null);
  const [slideIndex, setSlideIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;
    fetch('/api/me', { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.json())
      .then(setMe)
      .catch(() => {});
  }, []);

  const hasFetched = useRef(false);
  const loadRec = useCallback(async (userId: string) => {
    try {
      setError(null);
      let r = await fetch('/api/universities/recommendations?user_id=' + encodeURIComponent(userId) + '&top_k=1');
      let data = await r.json();
      let picked = data?.items?.[0];
      if (!picked) {
        // fallback to random if recommender empty
        r = await fetch('/api/universities/random');
        data = await r.json();
        picked = data;
      }
      if (picked?.error) throw new Error(picked.error);
      if (!picked?.images || picked.images.length === 0) {
        try {
          const res = await fetch(`/api/images/by-unitid/${picked.unitid}?limit=5`);
          const j = await res.json();
          if (j?.items?.length) picked.images = j.items;
        } catch {}
      }
      setUni(picked);
      setSlideIndex(0);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  const lastUidRef = useRef<string | null>(null);
  useEffect(() => {
    if (!me?.user_id) return;
    if (lastUidRef.current === me.user_id) return;
    lastUidRef.current = me.user_id;
    loadRec(me.user_id);
  }, [me?.user_id, loadRec]);

  const userSatTotal = useMemo(() => {
    if (!me) return undefined;
    if (me.sat_erw && me.sat_math) return (me.sat_erw || 0) + (me.sat_math || 0);
    return undefined;
  }, [me]);

  const bars: Array<{ label: string; value?: number; max?: number }> = useMemo(() => {
    if (!uni) return [];
    return [
      { label: 'Acceptance rate', value: uni.percent_admitted_total, max: 100 },
      { label: 'Yield', value: uni.admissions_yield_total, max: 100 },
      { label: 'Women %', value: uni.percent_of_undergraduate_enrollment_that_are_women, max: 100 },
      { label: 'Full-time retention', value: uni.full_time_retention_rate_2023, max: 100 },
      { label: 'Graduation rate', value: uni.graduation_rate_total_cohort, max: 100 },
    ];
  }, [uni]);

  const satBands = useMemo(() => {
    if (!uni) return null;
    return {
      erw: [
        uni.sat_evidence_based_reading_and_writing_25th_percentile_score,
        uni.sat_evidence_based_reading_and_writing_50th_percentile_score,
        uni.sat_evidence_based_reading_and_writing_75th_percentile_score,
      ],
      math: [
        uni.sat_math_25th_percentile_score,
        uni.sat_math_50th_percentile_score,
        uni.sat_math_75th_percentile_score,
      ],
    };
  }, [uni]);

  if (error) return (
    <div className="container">
      <div className="error-message">
        <span>⚠️</span>
        {error}
      </div>
    </div>
  );
  
  if (!uni) return (
    <div className="container">
      <div style={{ textAlign: 'center', padding: '60px 20px' }}>
        <div className="loading-spinner" style={{ width: 40, height: 40, margin: '0 auto 20px' }} />
        <div className="muted">Loading university recommendations...</div>
      </div>
    </div>
  );

  // Build slides: each slide shows an image + a focused info block. Last slide is image + like/dislike.
  const slides: Array<JSX.Element> = [];
  const imgs = (uni.images as ImageItem[] | undefined) || [];
  const getImg = (i: number) => imgs.length ? imgs[i % imgs.length].image_url : undefined;

  // Slide 1: Hero + quick facts
  slides.push(
    <TwoCol img={getImg(0)} alt={uni.institution_name}>
      <h3 style={{ color: 'var(--brand)', marginBottom: 20 }}>🏛️ Quick Facts</h3>
      <div style={{ 
        background: 'rgba(99, 102, 241, 0.05)', 
        border: '1px solid rgba(99, 102, 241, 0.2)', 
        borderRadius: 'var(--radius-sm)', 
        padding: '20px',
        marginBottom: 20
      }}>
        <ul style={{ margin: 0, padding: 0 }}>
          <li style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            padding: '12px 0',
            borderBottom: '1px solid rgba(99, 102, 241, 0.1)'
          }}>
            <strong>Acceptance rate:</strong> 
            <span style={{ color: 'var(--brand)', fontWeight: 600 }}>{naPct(uni.percent_admitted_total)}</span>
          </li>
          <li style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            padding: '12px 0',
            borderBottom: '1px solid rgba(99, 102, 241, 0.1)'
          }}>
            <strong>Control:</strong> 
            <span>{na(uni.control_of_institution)}</span>
          </li>
          <li style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            padding: '12px 0',
            borderBottom: '1px solid rgba(99, 102, 241, 0.1)'
          }}>
            <strong>Level:</strong> 
            <span>{na(uni.level_of_institution)}</span>
          </li>
          <li style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            padding: '12px 0',
            borderBottom: '1px solid rgba(99, 102, 241, 0.1)'
          }}>
            <strong>Locale:</strong> 
            <span>{na(uni.degree_of_urbanization_urban_centric_locale)}</span>
          </li>
          <li style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            padding: '12px 0'
          }}>
            <strong>Student/Faculty:</strong> 
            <span>{naNum(uni.student_to_faculty_ratio)}</span>
          </li>
        </ul>
      </div>
      <div style={{ marginTop: 8 }}>
        <strong>Website:</strong> {uni.institutions_internet_website_address ? (
          <a href={uni.institutions_internet_website_address} target="_blank" rel="noreferrer" style={{ marginLeft: 8 }}>
            🌐 Visit Website
          </a>
        ) : 'N/A'}
      </div>
    </TwoCol>
  );

  // Slide 2: Costs + map
  slides.push(
    <TwoCol img={getImg(1)} alt={uni.institution_name}>
      <h3 style={{ color: 'var(--brand-2)', marginBottom: 20 }}>💰 Costs & Financial Aid</h3>
      <div style={{ 
        background: 'rgba(16, 185, 129, 0.05)', 
        border: '1px solid rgba(16, 185, 129, 0.2)', 
        borderRadius: 'var(--radius-sm)', 
        padding: '20px',
        marginBottom: 20
      }}>
        <ul style={{ margin: 0, padding: 0 }}>
          <li style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            padding: '12px 0',
            borderBottom: '1px solid rgba(16, 185, 129, 0.1)'
          }}>
            <strong>Tuition/Fees:</strong> 
            <span style={{ color: 'var(--brand-2)', fontWeight: 600 }}>{money(uni.tuition_and_fees_2023_24)}</span>
          </li>
          <li style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            padding: '12px 0',
            borderBottom: '1px solid rgba(16, 185, 129, 0.1)'
          }}>
            <strong>In-state total:</strong> 
            <span>{money(uni.total_price_for_in_state_students_living_on_campus_2023_24)}</span>
          </li>
          <li style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            padding: '12px 0',
            borderBottom: '1px solid rgba(16, 185, 129, 0.1)'
          }}>
            <strong>Out-of-state total:</strong> 
            <span>{money(uni.total_price_for_out_of_state_students_living_on_campus_2023_24)}</span>
          </li>
          <li style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            padding: '12px 0',
            borderBottom: '1px solid rgba(16, 185, 129, 0.1)'
          }}>
            <strong>Avg grant aid:</strong> 
            <span>{money(uni.average_amount_of_federal_state_local_or_institutional_grant_aid_awarded)}</span>
          </li>
          <li style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            padding: '12px 0'
          }}>
            <strong>Avg net price:</strong> 
            <span>{money(uni.average_net_price_students_awarded_grant_or_scholarship_aid_2022_23)}</span>
          </li>
        </ul>
      </div>
      <div style={{ marginTop: 8 }}>
        <MapEmbed name={uni.institution_name} city={uni.city_location_of_institution} state={uni.state_abbreviation} />
      </div>
    </TwoCol>
  );

  // Slide 3: Rates
  slides.push(
    <TwoCol img={getImg(2)} alt={uni.institution_name}>
      <h3 style={{ color: 'var(--brand)', marginBottom: 20 }}>📊 Key Statistics</h3>
      <div style={{ 
        background: 'rgba(99, 102, 241, 0.05)', 
        border: '1px solid rgba(99, 102, 241, 0.2)', 
        borderRadius: 'var(--radius-sm)', 
        padding: '20px'
      }}>
        {bars.map((b) => (
          <Bar key={b.label} label={b.label} value={b.value} max={b.max} />
        ))}
      </div>
    </TwoCol>
  );

  // Slide 4: Tests
  slides.push(
    <TwoCol img={getImg(3)} alt={uni.institution_name}>
      <h3 style={{ color: 'var(--brand-2)', marginBottom: 20 }}>📝 Test Score Ranges</h3>
      <div style={{ 
        background: 'rgba(16, 185, 129, 0.05)', 
        border: '1px solid rgba(16, 185, 129, 0.2)', 
        borderRadius: 'var(--radius-sm)', 
        padding: '20px',
        marginBottom: 20
      }}>
        <Band label="SAT ERW" values={satBands?.erw || []} user={me?.sat_erw} />
        <Band label="SAT Math" values={satBands?.math || []} user={me?.sat_math} />
      </div>
      
      <div style={{ 
        background: 'rgba(16, 185, 129, 0.05)', 
        border: '1px solid rgba(16, 185, 129, 0.2)', 
        borderRadius: 'var(--radius-sm)', 
        padding: '20px'
      }}>
        <h4 style={{ margin: '0 0 16px', color: 'var(--brand-2)' }}>ACT Composite</h4>
        <Band label="ACT" values={[uni.act_composite_25th_percentile_score, uni.act_composite_50th_percentile_score, uni.act_composite_75th_percentile_score]} user={me?.act_composite} max={36} />
      </div>
    </TwoCol>
  );

  return (
    <div className="container" style={{ maxWidth: 1200 }}>
      {/* University Header */}
      <div className="university-header">
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 16, marginBottom: 16 }}>
          <h1 style={{ margin: 0 }}>{uni.institution_name}</h1>
          <span className="muted" style={{ fontSize: 18 }}>
            📍 {na(uni.city_location_of_institution)}, {na(uni.state_abbreviation)}
          </span>
        </div>
        
        <div style={{ display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
          {uni.institutions_internet_website_address && (
            <a 
              href={uni.institutions_internet_website_address} 
              target="_blank" 
              rel="noreferrer"
              className="btn"
              style={{ textDecoration: 'none' }}
            >
              🌐 Visit Website
            </a>
          )}
          
          {me && (
            <div className="muted" style={{ fontSize: 14 }}>
              <strong>Your scores:</strong> {me.act_composite ? `ACT ${me.act_composite}` : 'ACT N/A'} | {userSatTotal ? `SAT ${userSatTotal}` : 'SAT N/A'}
            </div>
          )}
        </div>
      </div>

      {/* Slides Navigation */}
      <Slides 
        index={slideIndex} 
        onIndex={setSlideIndex} 
        slides={slides} 
        footer={(atEnd) => (
          <div style={{ 
            display: 'flex', 
            gap: 16, 
            marginTop: 32, 
            justifyContent: 'center',
            flexWrap: 'wrap'
          }}>
            {!atEnd ? (
              <div style={{ 
                textAlign: 'center', 
                color: 'var(--muted)', 
                padding: '20px',
                background: 'rgba(255, 255, 255, 0.03)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)'
              }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>📖</div>
                <div>Flip through slides to learn more about this college</div>
                <div style={{ fontSize: 12, marginTop: 8 }}>Use arrow keys or navigation buttons</div>
              </div>
            ) : (
              <>
                <SwipeButton kind="dislike" unitid={uni.unitid} onDone={() => me?.user_id && loadRec(me.user_id)} />
                <SwipeButton kind="like" unitid={uni.unitid} onDone={() => me?.user_id && loadRec(me.user_id)} />
              </>
            )}
          </div>
        )} 
      />
    </div>
  );
}

function Bar({ label, value, max = 100 }: { label: string; value?: number; max?: number }) {
  const pct = value != null ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, marginBottom: 8 }}>
        <span style={{ fontWeight: 500 }}>{label}</span>
        <span style={{ color: 'var(--brand)', fontWeight: 600 }}>{value != null ? `${value}%` : 'N/A'}</span>
      </div>
      <div style={{ 
        height: 10, 
        background: 'var(--panel)', 
        borderRadius: 'var(--radius-sm)', 
        border: '1px solid var(--border)',
        overflow: 'hidden'
      }}>
        <div style={{ 
          width: `${pct}%`, 
          height: '100%', 
          background: 'linear-gradient(90deg, var(--brand), var(--brand-2))', 
          borderRadius: 'var(--radius-sm)',
          transition: 'width 0.3s ease'
        }} />
      </div>
    </div>
  );
}

function Band({ label, values, user, max = 800 }: { label: string; values: Array<number | undefined>; user?: number; max?: number }) {
  const [p25, p50, p75] = values;
  const lo = p25 ?? undefined;
  const hi = p75 ?? undefined;
  const u = user;
  const getPct = (v?: number) =>
    v != null ? Math.max(0, Math.min(100, (v / (max || 1)) * 100)) : undefined;
  const pctLo = getPct(lo);
  const pctHi = getPct(hi);
  const pctUser = getPct(u);
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, marginBottom: 12 }}>
        <span style={{ fontWeight: 500 }}>{label}</span>
        <span style={{ color: 'var(--brand-2)', fontWeight: 600 }}>
          {p25 != null && p75 != null ? `${p25}–${p75}` : 'N/A'}
        </span>
      </div>
      <div style={{ 
        position: 'relative', 
        height: 12, 
        background: 'var(--panel)', 
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border)',
        overflow: 'hidden'
      }}>
        {pctLo != null && pctHi != null && (
          <div style={{ 
            position: 'absolute', 
            left: `${pctLo}%`, 
            width: `${Math.max(0, pctHi - pctLo)}%`, 
            top: 0, 
            bottom: 0, 
            background: 'linear-gradient(90deg, var(--brand-2), var(--ok))', 
            borderRadius: 'var(--radius-sm)'
          }} />
        )}
        {/* p25 marker */}
        {pctLo != null && (
          <div 
            title={`25th percentile: ${p25}`} 
            style={{ 
              position: 'absolute', 
              left: `${pctLo}%`, 
              top: -6, 
              width: 3, 
              height: 24, 
              background: 'var(--brand-2)', 
              borderRadius: '2px'
            }} 
          />
        )}
        {/* p50 marker */}
        {p50 != null && (
          <div 
            title={`50th percentile: ${p50}`} 
            style={{ 
              position: 'absolute', 
              left: `${getPct(p50)}%`, 
              top: -4, 
              width: 3, 
              height: 20, 
              background: 'var(--ok)', 
              borderRadius: '2px'
            }} 
          />
        )}
        {/* p75 marker */}
        {pctHi != null && (
          <div 
            title={`75th percentile: ${p75}`} 
            style={{ 
              position: 'absolute', 
              left: `${pctHi}%`, 
              top: -6, 
              width: 3, 
              height: 24, 
              background: 'var(--brand-2)', 
              borderRadius: '2px'
            }} 
          />
        )}
        {/* user marker */}
        {pctUser != null && (
          <div 
            title={`Your score: ${user}`} 
            style={{ 
              position: 'absolute', 
              left: `${pctUser}%`, 
              top: -5, 
              width: 3, 
              height: 22, 
              background: 'var(--brand)', 
              borderRadius: '2px',
              boxShadow: '0 0 8px rgba(99, 102, 241, 0.6)'
            }} 
          />
        )}
      </div>
      {p50 != null && (
        <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 6 }}>
          <strong>Median:</strong> {p50}
        </div>
      )}
    </div>
  );
}

function SwipeButton({ kind, unitid, onDone }: { kind: 'like' | 'dislike'; unitid: number; onDone?: () => void }) {
  const [loading, setLoading] = useState(false);
  const token = localStorage.getItem('token');
  const onClick = async () => {
    if (!token) return;
    setLoading(true);
    try {
      await fetch(`/api/${kind === 'like' ? 'likes' : 'dislikes'}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ unitid }),
      });
      // Fetch the next random university immediately after action without full reload
      onDone?.();
    } finally {
      setLoading(false);
    }
  };
  return (
    <button 
      onClick={onClick} 
      disabled={loading} 
      className={`btn ${kind === 'like' ? 'ok' : 'danger'}`}
      style={{ padding: '16px 32px', fontSize: 16 }}
    >
      {loading ? (
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div className="loading-spinner" />
          {kind === 'like' ? 'Liking...' : 'Disliking...'}
        </span>
      ) : (
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {kind === 'like' ? '👍 Like' : '👎 Dislike'}
        </span>
      )}
    </button>
  );
}

function Slides({ slides, footer, index, onIndex }: { slides: Array<JSX.Element>; footer?: (atEnd: boolean) => JSX.Element; index: number; onIndex: (n: number) => void }) {
  const atEnd = index >= slides.length - 1;
  const prev = () => onIndex(Math.max(0, index - 1));
  const next = () => onIndex(Math.min(slides.length - 1, index + 1));

  // keyboard navigation
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') next();
      if (e.key === 'ArrowLeft') prev();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // touch swipe
  const [touchX, setTouchX] = useState<number | null>(null);
  const onTouchStart = (e: React.TouchEvent) => setTouchX(e.touches[0].clientX);
  const onTouchEnd = (e: React.TouchEvent) => {
    if (touchX == null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    if (dx > 40) prev();
    if (dx < -40) next();
    setTouchX(null);
  };

  return (
    <div onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
      {/* Navigation Controls */}
      <div style={{ 
        marginBottom: 24, 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        background: 'rgba(255, 255, 255, 0.03)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '16px 20px'
      }}>
        <div style={{ display: 'flex', gap: 8 }}>
          {slides.map((_, i) => (
            <div 
              key={i} 
              className={`dot ${i === index ? 'active' : ''}`}
              onClick={() => onIndex(i)}
              style={{ cursor: 'pointer' }}
            />
          ))}
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button 
            className="btn" 
            onClick={prev} 
            disabled={index === 0}
            style={{ padding: '8px 16px' }}
          >
            ← Back
          </button>
          <button 
            className="btn" 
            onClick={next} 
            disabled={atEnd}
            style={{ padding: '8px 16px' }}
          >
            Next →
          </button>
        </div>
      </div>
      
      {/* Current Slide */}
      <div style={{ animation: 'fadeInUp 0.4s ease-out' }}>{slides[index]}</div>
      
      {/* Footer */}
      {footer ? footer(atEnd) : null}
    </div>
  );
}

function MapEmbed({ name, city, state }: { name?: string; city?: string; state?: string }) {
  const q = encodeURIComponent([name, city, state, 'United States'].filter(Boolean).join(', '));
  // Google Maps embed via query. Start zoomed out via 
  const url = `https://www.google.com/maps?q=${q}&output=embed&z=4`;
  return (
    <div style={{ 
      border: '1px solid var(--border)', 
      borderRadius: 'var(--radius-sm)', 
      overflow: 'hidden'
    }}>
      <iframe 
        title="map" 
        src={url} 
        style={{ width: '100%', height: 240, border: 0 }} 
      />
    </div>
  );
}

function na(v?: string) { return v && v.trim().length ? v : 'N/A'; }
function naNum(v?: number) { return v != null ? String(v) : 'N/A'; }
function naPct(v?: number) { return v != null ? `${v}%` : 'N/A'; }
function num(v?: number) { return v != null ? v.toLocaleString?.() : 'N/A' as any; }
function money(v?: number) { return v != null ? `$${v.toLocaleString?.()}` : 'N/A'; }



