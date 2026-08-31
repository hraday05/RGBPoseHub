import { NavLink } from 'react-router-dom';

export default function Sidebar({ user, isOpen, onClose }) {
  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
      <div className="sidebar-brand">
        <h1>RGB-Pose Hub</h1>
        <p>6D Pose Estimation Platform</p>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={onClose}>
          <span className="nav-icon">📊</span>
          <span>Dashboard</span>
        </NavLink>
        <NavLink to="/analysis" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={onClose}>
          <span className="nav-icon">🔬</span>
          <span>Image Analysis</span>
        </NavLink>
        <NavLink to="/dataset" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={onClose}>
          <span className="nav-icon">🗂️</span>
          <span>Dataset (CLUBS)</span>
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={onClose}>
          <span className="nav-icon">📋</span>
          <span>Activity History</span>
        </NavLink>
        <NavLink to="/profile" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={onClose}>
          <span className="nav-icon">👤</span>
          <span>Profile & 2FA</span>
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Logged in as:
        </div>
        <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--accent-blue)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {user?.full_name || user?.username || 'User'}
        </div>
      </div>
    </aside>
  );
}
