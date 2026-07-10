import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { api } from '../api';
import ThemeToggle from './ThemeToggle';

type NavItem = { to: string; label: string; icon: string; end?: boolean; key?: string };

// Grouped so the (long) tab strip stays scannable; a thin divider separates groups.
const groups: NavItem[][] = [
  [{ to: '/', label: 'Dashboard', icon: '◍', end: true }],
  [
    { to: '/schedule', label: 'Schedule', icon: '▦' },
    { to: '/catalog', label: 'Providers', icon: '⚕' },
    { to: '/appointments', label: 'Appointments', icon: '❖' },
    { to: '/waitlist', label: 'Waitlist', icon: '☰' },
  ],
  [
    { to: '/patients', label: 'Patients', icon: '❑' },
    { to: '/insurance', label: 'Insurance', icon: '⛨' },
  ],
  [
    { to: '/escalations', label: 'Escalations', icon: '⚠', key: 'escalations' },
    { to: '/communications', label: 'Messages', icon: '✉' },
    { to: '/reminders', label: 'Reminders', icon: '⏰' },
    { to: '/campaigns', label: 'Campaigns', icon: '⇲' },
  ],
  [
    { to: '/calls', label: 'Calls', icon: '◈' },
    { to: '/transcripts', label: 'Transcripts', icon: '☲' },
    { to: '/insights', label: 'Insights', icon: '◑' },
  ],
  [
    { to: '/simulator', label: 'Simulator', icon: '⟐' },
    { to: '/demo', label: 'Guided demo', icon: '▶' },
  ],
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [openEscalations, setOpenEscalations] = useState(0);

  useEffect(() => {
    api
      .get<{ count: number }>('/api/escalations/open-count')
      .then((r) => setOpenEscalations(r?.count ?? 0))
      .catch(() => {});
  }, []);

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
          {groups.map((group, gi) => (
            <div className="tab-group" key={gi}>
              {gi > 0 && <span className="tab-divider" aria-hidden="true" />}
              {group.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  role="tab"
                  className={({ isActive }) => 'tab' + (isActive ? ' active' : '')}
                >
                  <span className="tab-icon" aria-hidden="true">{item.icon}</span>
                  <span className="tab-label">{item.label}</span>
                  {item.key === 'escalations' && openEscalations > 0 && (
                    <span className="tab-badge">{openEscalations}</span>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="topbar-user">
          <ThemeToggle />
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
