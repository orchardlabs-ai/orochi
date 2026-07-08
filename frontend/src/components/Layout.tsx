import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';

const nav = [
  { to: '/', label: 'Dashboard', icon: '📊', end: true },
  { to: '/patients', label: 'Patients', icon: '🧑‍⚕️' },
  { to: '/appointments', label: 'Appointments', icon: '📅' },
  { to: '/calls', label: 'Calls', icon: '📞' },
  { to: '/simulator', label: 'Simulator', icon: '🧪' },
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
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">🐉</span>
          <div>
            <div className="brand-name">Orochi</div>
            <div className="brand-sub">Clinic Voice Agent</div>
          </div>
        </div>

        <nav className="nav">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                'nav-link' + (isActive ? ' active' : '')
              }
            >
              <span className="nav-icon" aria-hidden="true">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-chip">
            <div className="avatar" aria-hidden="true">
              {user?.email.charAt(0).toUpperCase()}
            </div>
            <div className="user-meta">
              <div className="user-email" title={user?.email}>{user?.email}</div>
              <div className="user-role">Administrator</div>
            </div>
          </div>
          <button className="btn btn-ghost btn-block" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </aside>

      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
