import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';

const nav = [
  { to: '/', label: 'Dashboard', icon: '◍', end: true },
  { to: '/patients', label: 'Patients', icon: '❑' },
  { to: '/appointments', label: 'Appointments', icon: '❖' },
  { to: '/calls', label: 'Calls', icon: '◈' },
  { to: '/simulator', label: 'Simulator', icon: '⟐' },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">🐉</span>
          <div className="brand-text">
            <span className="brand-name">Orochi</span>
            <span className="brand-sub">Clinic Voice Agent</span>
          </div>
        </div>

        <nav className="tabs" role="tablist" aria-label="Primary">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              role="tab"
              className={({ isActive }) => 'tab' + (isActive ? ' active' : '')}
            >
              <span className="tab-icon" aria-hidden="true">{item.icon}</span>
              <span className="tab-label">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="topbar-user">
          <div className="user-chip">
            <div className="avatar" aria-hidden="true">
              {user?.email.charAt(0).toUpperCase()}
            </div>
            <div className="user-meta">
              <div className="user-email" title={user?.email}>{user?.email}</div>
              <div className="user-role">Administrator</div>
            </div>
          </div>
          <button className="btn btn-ghost" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </header>

      <main className="content">
        <div className="content-inner">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
