import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';

export default function Topbar() {
  const loc = useLocation();
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  
  const active = (p: string) => (loc.pathname === p ? 'active' : '');
  
  useEffect(() => {
    const token = localStorage.getItem('token');
    setIsAuthenticated(!!token);
  }, [loc.pathname]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    navigate('/');
  };

  return (
    <div className="toolbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div className="pill" style={{ width: 36, height: 36 }} />
        <div className="brand" style={{ fontSize: 20 }}>College Matcher</div>
      </div>
      <nav className="nav">
        {isAuthenticated ? (
          <>
            <Link className={active('/profile')} to="/profile">
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                🎓 Discover
              </span>
            </Link>
            <Link className={active('/search')} to="/search">
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                🔍 Search
              </span>
            </Link>
            <Link className={active('/analysis')} to="/analysis">
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                🧠 Analysis
              </span>
            </Link>
            <Link className={active('/account')} to="/account">
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                👤 Profile
              </span>
            </Link>
            <button 
              onClick={handleLogout}
              className="btn logout"
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                🚪 Logout
              </span>
            </button>
          </>
        ) : (
          <>
            <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              🔑 Sign In
            </Link>
            <Link to="/signup" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              ✨ Sign Up
            </Link>
          </>
        )}
      </nav>
    </div>
  );
}


