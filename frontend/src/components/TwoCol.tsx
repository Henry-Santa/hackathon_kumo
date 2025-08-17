import React from 'react';

export default function TwoCol({ img, alt, children }: { img?: string; alt: string; children: React.ReactNode }) {
  return (
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: '2fr 3fr', 
      gap: 24, 
      alignItems: 'start',
      minHeight: 400
    }}>
      <div>
        {img ? (
          <div className="image-gallery">
            <img 
              src={img} 
              alt={alt} 
              style={{ 
                width: '100%', 
                height: 360, 
                objectFit: 'cover', 
                borderRadius: 'var(--radius)',
                transition: 'transform 0.3s ease'
              }} 
            />
          </div>
        ) : (
          <div style={{ 
            width: '100%', 
            height: 360, 
            background: 'linear-gradient(135deg, var(--panel), var(--panel-hover))', 
            border: '1px solid var(--border)', 
            borderRadius: 'var(--radius)', 
            display: 'grid', 
            placeItems: 'center', 
            color: 'var(--muted)',
            fontSize: 16
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>🏛️</div>
              <div>No image available</div>
            </div>
          </div>
        )}
      </div>
      <div style={{ padding: '8px 0' }}>
        {children}
      </div>
    </div>
  );
}


