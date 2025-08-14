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
      <div style={{ fontWeight: 800 }}>College Matcher</div>
      <nav className="nav" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        {isAuthenticated ? (
          <>
            <Link className={active('/profile')} to="/profile">Discover</Link>
            <Link className={active('/search')} to="/search">Search</Link>
            <Link className={active('/account')} to="/account">Profile</Link>
            <button 
              onClick={handleLogout}
              className="btn logout"
            >
              Logout
            </button>
          </>
        ) : (
          <>
            <Link to="/">Sign In</Link>
            <Link to="/signup">Sign Up</Link>
          </>
        )}
      </nav>
    </div>
  );
}


