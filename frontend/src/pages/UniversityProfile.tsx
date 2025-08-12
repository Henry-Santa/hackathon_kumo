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
  const loadRandom = useCallback(async () => {
    try {
      setError(null);
      const r = await fetch('/api/universities/random');
      const data = await r.json();
      if (data?.error) throw new Error(data.error);
      if (!data?.images || data.images.length === 0) {
        try {
          const res = await fetch(`/api/images/by-unitid/${data.unitid}?limit=5`);
          const j = await res.json();
          if (j?.items?.length) data.images = j.items;
        } catch {}
      }
      setUni(data);
      setSlideIndex(0);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    if (hasFetched.current) return; // guard StrictMode double-invoke
    hasFetched.current = true;
    loadRandom();
  }, [loadRandom]);

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

  if (error) return <p style={{ color: 'crimson' }}>{error}</p>;
  if (!uni) return <p>Loading university…</p>;

  // Build slides: each slide shows an image + a focused info block. Last slide is image + like/dislike.
  const slides: Array<JSX.Element> = [];
  const imgs = (uni.images as ImageItem[] | undefined) || [];
  const getImg = (i: number) => imgs.length ? imgs[i % imgs.length].image_url : undefined;

  // Slide 1: Hero + quick facts
  slides.push(
    <TwoCol img={getImg(0)} alt={uni.institution_name}>
      <h3>Quick facts</h3>
      <ul>
        <li><strong>Acceptance rate:</strong> {naPct(uni.percent_admitted_total)}</li>
        <li>Control: {na(uni.control_of_institution)}</li>
        <li>Level: {na(uni.level_of_institution)}</li>
        <li>Locale: {na(uni.degree_of_urbanization_urban_centric_locale)}</li>
        <li>Student/Faculty: {naNum(uni.student_to_faculty_ratio)}</li>
      </ul>
      <div style={{ marginTop: 8 }}>
        Website: {uni.institutions_internet_website_address ? <a href={uni.institutions_internet_website_address} target="_blank" rel="noreferrer">link</a> : 'N/A'}
      </div>
    </TwoCol>
  );

  // Slide 2: Costs + map
  slides.push(
    <TwoCol img={getImg(1)} alt={uni.institution_name}>
      <h3>Costs</h3>
      <ul>
        <li>Tuition/Fees: {money(uni.tuition_and_fees_2023_24)}</li>
        <li>In-state total: {money(uni.total_price_for_in_state_students_living_on_campus_2023_24)}</li>
        <li>Out-of-state total: {money(uni.total_price_for_out_of_state_students_living_on_campus_2023_24)}</li>
        <li>Avg grant aid: {money(uni.average_amount_of_federal_state_local_or_institutional_grant_aid_awarded)}</li>
        <li>Avg net price (22-23): {money(uni.average_net_price_students_awarded_grant_or_scholarship_aid_2022_23)}</li>
      </ul>
      <div style={{ marginTop: 8 }}>
        <MapEmbed name={uni.institution_name} city={uni.city_location_of_institution} state={uni.state_abbreviation} />
      </div>
    </TwoCol>
  );

  // Slide 3: Rates
  slides.push(
    <TwoCol img={getImg(2)} alt={uni.institution_name}>
      <h3>Rates</h3>
      {bars.map((b) => (
        <Bar key={b.label} label={b.label} value={b.value} max={b.max} />
      ))}
    </TwoCol>
  );

  // Slide 4: Tests
  slides.push(
    <TwoCol img={getImg(3)} alt={uni.institution_name}>
      <h3>SAT bands</h3>
      <Band label="ERW" values={satBands?.erw || []} user={me?.sat_erw} />
      <Band label="Math" values={satBands?.math || []} user={me?.sat_math} />
      <h3 style={{ marginTop: 16 }}>ACT composite</h3>
      <Band label="ACT" values={[uni.act_composite_25th_percentile_score, uni.act_composite_50th_percentile_score, uni.act_composite_75th_percentile_score]} user={me?.act_composite} max={36} />
    </TwoCol>
  );

  return (
    <div style={{ maxWidth: 1000, margin: '24px auto', fontFamily: 'Inter, system-ui, Arial', padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
        <h1 style={{ margin: 0 }}>{uni.institution_name}</h1>
        <span style={{ color: '#666' }}>{na(uni.city_location_of_institution)}, {na(uni.state_abbreviation)}</span>
      </div>
      <div style={{ display: 'flex', gap: 16, margin: '8px 0 16px' }}>
        <a href={uni.institutions_internet_website_address || '#'} target="_blank" rel="noreferrer">Website</a>
        {me && (
          <span style={{ color: '#444' }}>
            Your scores: {me.act_composite ? `ACT ${me.act_composite}` : 'ACT N/A'} | {userSatTotal ? `SAT ${userSatTotal}` : 'SAT N/A'}
          </span>
        )}
      </div>

      <Slides index={slideIndex} onIndex={setSlideIndex} slides={slides} footer={(atEnd) => (
        <div style={{ display: 'flex', gap: 12, marginTop: 16, justifyContent: 'center' }}>
          {!atEnd ? <span style={{ color: '#666' }}>Flip through slides, then choose Like/Dislike</span> : (
            <>
              <SwipeButton kind="dislike" unitid={uni.unitid} onDone={loadRandom} />
              <SwipeButton kind="like" unitid={uni.unitid} onDone={loadRandom} />
            </>
          )}
        </div>
      )} />
    </div>
  );
}

function Bar({ label, value, max = 100 }: { label: string; value?: number; max?: number }) {
  const pct = value != null ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
        <span>{label}</span>
        <span>{value != null ? `${value}%` : 'N/A'}</span>
      </div>
      <div style={{ height: 8, background: '#eee', borderRadius: 4 }}>
        <div style={{ width: `${pct}%`, height: '100%', background: '#4f46e5', borderRadius: 4 }} />
      </div>
    </div>
  );
}

function Band({ label, values, user, max = 800 }: { label: string; values: Array<number | undefined>; user?: number; max?: number }) {
  const [p25, p50, p75] = values;
  const lo = p25 ?? undefined;
  const hi = p75 ?? undefined;
  const u = user;
  const pct = (v?: number) => (v != null ? Math.max(0, Math.min(100, (v / (max || 1)) * 100)) : undefined);
  const pctLo = pct(lo);
  const pctHi = pct(hi);
  const pctUser = pct(u);
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
        <span>{label}</span>
        <span>{p25 != null && p75 != null ? `${p25}–${p75}` : 'N/A'}</span>
      </div>
      <div style={{ position: 'relative', height: 10, background: '#eee', borderRadius: 5 }}>
        {pctLo != null && pctHi != null && (
          <div style={{ position: 'absolute', left: `${pctLo}%`, width: `${Math.max(0, pctHi - pctLo)}%`, top: 0, bottom: 0, background: '#10b981', borderRadius: 5 }} />
        )}
        {/* p25 marker */}
        {pctLo != null && <div title={`25th: ${p25}`} style={{ position: 'absolute', left: `${pctLo}%`, top: -4, width: 2, height: 18, background: '#065f46' }} />}
        {/* p50 marker */}
        {p50 != null && (
          <div title={`50th: ${p50}`} style={{ position: 'absolute', left: `${pct(p50)}%`, top: -2, width: 2, height: 14, background: '#047857' }} />
        )}
        {/* p75 marker */}
        {pctHi != null && <div title={`75th: ${p75}`} style={{ position: 'absolute', left: `${pctHi}%`, top: -4, width: 2, height: 18, background: '#065f46' }} />}
        {/* user marker */}
        {pctUser != null && (
          <div title={`You: ${user}`} style={{ position: 'absolute', left: `${pctUser}%`, top: -3, width: 2, height: 16, background: '#111827' }} />
        )}
      </div>
      {p50 != null && <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>Median: {p50}</div>}
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
    <button onClick={onClick} disabled={loading} style={{ padding: '10px 16px', borderRadius: 8, border: '1px solid #ddd' }}>
      {kind === 'like' ? '👍 Like' : '👎 Dislike'}
    </button>
  );
}

/* TwoCol is imported from ../components/TwoCol */

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
      <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 6 }}>
          {slides.map((_, i) => (
            <div key={i} className={`dot ${i === index ? 'active' : ''}`} />
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={prev} disabled={index === 0}>Back</button>
          <button onClick={next} disabled={atEnd}>Next</button>
        </div>
      </div>
      <div>{slides[index]}</div>
      {footer ? footer(atEnd) : null}
    </div>
  );
}

function Carousel({ images, alt }: { images: string[]; alt: string }) {
  const [idx, setIdx] = useState(0);
  const prev = () => setIdx((i) => (i - 1 + images.length) % images.length);
  const next = () => setIdx((i) => (i + 1) % images.length);
  if (!images.length) return null;
  return (
    <div>
      <div style={{ position: 'relative' }}>
        <img src={images[idx]} alt={alt} style={{ width: '100%', maxHeight: 360, objectFit: 'cover', borderRadius: 8 }} />
        {images.length > 1 && (
          <div style={{ position: 'absolute', bottom: 8, right: 8, display: 'flex', gap: 8 }}>
            <button onClick={prev}>Prev</button>
            <button onClick={next}>Next</button>
          </div>
        )}
      </div>
      {images.length > 1 && (
        <div style={{ display: 'flex', gap: 6, marginTop: 6, justifyContent: 'center' }}>
          {images.map((_, i) => (
            <div key={i} style={{ width: 6, height: 6, borderRadius: 999, background: i === idx ? '#4f46e5' : '#d1d5db' }} />
          ))}
        </div>
      )}
    </div>
  );
}

function MapEmbed({ name, city, state }: { name?: string; city?: string; state?: string }) {
  const q = encodeURIComponent([name, city, state, 'United States'].filter(Boolean).join(', '));
  // Google Maps embed via query. Start zoomed out via 
  const url = `https://www.google.com/maps?q=${q}&output=embed&z=4`;
  return <iframe title="map" src={url} style={{ width: '100%', height: 220, border: 0, borderRadius: 8 }} />;
}

function na(v?: string) { return v && v.trim().length ? v : 'N/A'; }
function naNum(v?: number) { return v != null ? String(v) : 'N/A'; }
function naPct(v?: number) { return v != null ? `${v}%` : 'N/A'; }
function num(v?: number) { return v != null ? v.toLocaleString?.() : 'N/A' as any; }
function money(v?: number) { return v != null ? `$${v.toLocaleString?.()}` : 'N/A'; }


