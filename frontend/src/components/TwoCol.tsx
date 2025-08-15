import React from 'react';

export default function TwoCol({ img, alt, children }: { img?: string; alt: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '2fr 3fr', gap: 16, alignItems: 'start' }}>
      <div>
        {img ? (
          <img src={img} alt={alt} style={{ width: '100%', maxHeight: 320, objectFit: 'cover', borderRadius: 8 }} />
        ) : (
          <div style={{ width: '100%', height: 200, background: '#0f1428', border: '1px solid var(--border)', borderRadius: 12, display: 'grid', placeItems: 'center', color: 'var(--muted)' }}>No image</div>
        )}
      </div>
      <div>
        {children}
      </div>
    </div>
  );
}


