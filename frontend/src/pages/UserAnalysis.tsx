import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

interface AdmissionChance {
  college_name: string;
  assessment: string;
}

interface UserAnalysis {
  general_description: string;
  college_preferences: string;
  admission_chances: AdmissionChance[];
}

const UserAnalysis: React.FC = () => {
  const [analysis, setAnalysis] = useState<UserAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAnalysis();
  }, []);

  const fetchAnalysis = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        navigate('/');
        return;
      }

      const response = await fetch('/api/me/analysis', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 503) {
          setError('AI analysis service is not available. Please try again later.');
        } else {
          setError('Failed to fetch analysis. Please try again.');
        }
        setLoading(false);
        return;
      }

      const data = await response.json();
      setAnalysis(data);
    } catch (err) {
      setError('An error occurred while fetching your analysis.');
      console.error('Error fetching analysis:', err);
    } finally {
      setLoading(false);
    }
  };

  const getClassificationColor = (assessment: string) => {
    if (assessment.includes('REACH')) return 'text-danger';
    if (assessment.includes('TARGET')) return 'text-muted';
    if (assessment.includes('LIKELY')) return 'text-brand';
    if (assessment.includes('SAFETY')) return 'text-success';
    return 'text-muted';
  };

  if (loading) {
    return (
      <div className="container">
        <div className="card text-center">
          <div className="loading-spinner" style={{ margin: '0 auto 20px' }}></div>
          <p className="text-muted">Analyzing your college preferences...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="card text-center" style={{ maxWidth: '500px', margin: '0 auto' }}>
          <div style={{ fontSize: '48px', marginBottom: '20px' }}>⚠️</div>
          <h2 className="text-xl font-semibold mb-2">Analysis Unavailable</h2>
          <p className="text-muted mb-4">{error}</p>
          <button
            onClick={fetchAnalysis}
            className="btn primary"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="mb-6">
        <h1 className="title">Your College Analysis</h1>
        <p className="text-muted">AI-powered insights into your college preferences and admission chances</p>
      </div>

      {analysis && (
        <div className="grid" style={{ gap: '24px' }}>
          {/* General Description Section */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4" style={{ display: 'flex', alignItems: 'center' }}>
              <span style={{ 
                background: 'var(--brand)', 
                color: 'white', 
                padding: '8px', 
                borderRadius: '50%', 
                marginRight: '12px',
                fontSize: '16px'
              }}>
                🎯
              </span>
              General Preferences
            </h2>
            <p className="text-secondary">{analysis.general_description}</p>
          </div>

          {/* College Preferences Section */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4" style={{ display: 'flex', alignItems: 'center' }}>
              <span style={{ 
                background: 'var(--ok)', 
                color: 'white', 
                padding: '8px', 
                borderRadius: '50%', 
                marginRight: '12px',
                fontSize: '16px'
              }}>
                💡
              </span>
              What You Value in Colleges
            </h2>
            <p className="text-secondary">{analysis.college_preferences}</p>
          </div>

          {/* Admission Chances Section */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4" style={{ display: 'flex', alignItems: 'center' }}>
              <span style={{ 
                background: 'var(--brand-2)', 
                color: 'white', 
                padding: '8px', 
                borderRadius: '50%', 
                marginRight: '12px',
                fontSize: '16px'
              }}>
                📊
              </span>
              Admission Chances
            </h2>
            {analysis.admission_chances.length > 0 ? (
              <div style={{ display: 'grid', gap: '12px' }}>
                {analysis.admission_chances.map((chance, index) => (
                  <div key={index} style={{ 
                    borderLeft: '4px solid var(--border)', 
                    paddingLeft: '16px', 
                    padding: '8px 0 8px 16px' 
                  }}>
                    <h3 className="font-medium mb-1">{chance.college_name}</h3>
                    <p className={getClassificationColor(chance.assessment)}>
                      {chance.assessment}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted italic">No admission chances analysis available.</p>
            )}
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', paddingTop: '24px' }}>
            <button
              onClick={() => navigate('/search')}
              className="btn primary"
            >
              Discover More Colleges
            </button>
            <button
              onClick={() => navigate('/profile')}
              className="btn"
            >
              View Profile
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserAnalysis;
