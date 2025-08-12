import { Link, useLocation } from 'react-router-dom';

export default function Topbar() {
  const loc = useLocation();
  const active = (p: string) => (loc.pathname === p ? 'active' : '');
  return (
    <div className="toolbar">
      <div style={{ fontWeight: 800 }}>College Matcher</div>
      <nav className="nav" style={{ display: 'flex', gap: 6 }}>
        <Link className={active('/profile')} to="/profile">Discover</Link>
        <Link className={active('/search')} to="/search">Search</Link>
        <Link className={active('/account')} to="/account">Profile</Link>
      </nav>
    </div>
  );
}


