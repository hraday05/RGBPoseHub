import { useState, useEffect } from 'react';
import { authAPI } from '../services/api';

export default function ProfilePage({ user, onLogout }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState(user);
  const [editName, setEditName] = useState(user?.full_name || '');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const [profileRes, sessionsRes] = await Promise.all([
        authAPI.getProfile(),
        authAPI.getSessions(),
      ]);
      setProfile(profileRes.data.user);
      setEditName(profileRes.data.user.full_name || '');
      setSessions(sessionsRes.data.sessions || []);
    } catch (err) {
      console.error('Profile load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    try {
      const res = await authAPI.updateProfile({ full_name: editName });
      setProfile(res.data.user);
      setMessage('Profile updated successfully');
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      setMessage('Update failed');
    } finally {
      setSaving(false);
    }
  };

  const handleRevokeSession = async (sessionId) => {
    try {
      await authAPI.revokeSession(sessionId);
      setSessions(sessions.filter(s => s.id !== sessionId));
    } catch (err) {
      console.error('Revoke error:', err);
    }
  };

  const handleLogout = async () => {
    try {
      await authAPI.logout();
    } catch { /* ignore */ }
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    onLogout();
  };

  if (loading) {
    return <div className="loading-overlay"><div className="spinner" /><p>Loading profile...</p></div>;
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Profile & Settings</h2>
        <p>Manage your account, 2FA, and active sessions</p>
      </div>
      <div className="page-body">
        {message && <div className="alert alert-success">✓ {message}</div>}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          {/* Profile Info */}
          <div className="card">
            <h4 style={{ marginBottom: '1.25rem' }}>👤 Profile Information</h4>
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input className="form-input" type="text" value={editName}
                onChange={(e) => setEditName(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Email</label>
              <input className="form-input" type="email" value={profile?.email || ''} disabled
                style={{ opacity: 0.6 }} />
            </div>
            <div className="form-group">
              <label className="form-label">Username</label>
              <input className="form-input" type="text" value={profile?.username || ''} disabled
                style={{ opacity: 0.6 }} />
            </div>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving...' : '💾 Save Changes'}
              </button>
            </div>
          </div>

          {/* Security */}
          <div className="card">
            <h4 style={{ marginBottom: '1.25rem' }}>🛡️ Security</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)' }}>
                <div>
                  <p style={{ fontWeight: 600 }}>Two-Factor Authentication</p>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>TOTP-based 2FA via authenticator app</p>
                </div>
                <span className={`badge ${profile?.is_2fa_enabled ? 'badge-success' : 'badge-warning'}`}>
                  {profile?.is_2fa_enabled ? '🛡️ Enabled' : '⚠ Disabled'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)' }}>
                <div>
                  <p style={{ fontWeight: 600 }}>Role</p>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Your access level</p>
                </div>
                <span className="badge badge-purple">{profile?.role || 'researcher'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)' }}>
                <div>
                  <p style={{ fontWeight: 600 }}>Last Login</p>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Most recent sign-in</p>
                </div>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {profile?.last_login_at ? new Date(profile.last_login_at).toLocaleString() : 'N/A'}
                </span>
              </div>
            </div>
            <button className="btn btn-danger btn-sm" style={{ marginTop: '1.25rem' }} onClick={handleLogout}>
              🚪 Sign Out
            </button>
          </div>
        </div>

        {/* Active Sessions */}
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <div className="card-header">
            <h4 className="card-title">🖥️ Active Sessions</h4>
            <span className="badge badge-info">{sessions.length} active</span>
          </div>
          {sessions.length === 0 ? (
            <p style={{ color: 'var(--text-muted)' }}>No active sessions</p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Device / Browser</th>
                    <th>IP Address</th>
                    <th>Created</th>
                    <th>Expires</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((session) => (
                    <tr key={session.id}>
                      <td style={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.85rem' }}>
                        {session.user_agent || 'Unknown'}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{session.ip_address || '—'}</td>
                      <td style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                        {session.created_at ? new Date(session.created_at).toLocaleString() : '—'}
                      </td>
                      <td style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                        {session.expires_at ? new Date(session.expires_at).toLocaleString() : '—'}
                      </td>
                      <td>
                        <button className="btn btn-danger btn-sm" onClick={() => handleRevokeSession(session.id)}>
                          Revoke
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
