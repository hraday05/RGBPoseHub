import { useState, useEffect } from 'react';
import { authAPI, dataAPI, mlAPI } from '../services/api';

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [datasetStatus, setDatasetStatus] = useState(null);
  const [modelStatus, setModelStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [statsRes, dataRes, mlRes] = await Promise.all([
        authAPI.getStats().catch(() => null),
        dataAPI.getStatus().catch(() => null),
        mlAPI.getStatus().catch(() => null),
      ]);
      if (statsRes) {
        setStats(statsRes.data.stats);
        setRecentActivity(statsRes.data.recent_activity || []);
      }
      if (dataRes) setDatasetStatus(dataRes.data.dataset);
      if (mlRes) setModelStatus(mlRes.data);
    } catch (err) {
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (iso) => {
    if (!iso) return '';
    const d = new Date(iso);
    const now = new Date();
    const diff = (now - d) / 1000;
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return d.toLocaleDateString();
  };

  const actionIcons = {
    login_success: '🔐', logout: '👋', register: '🆕', image_upload: '📤',
    image_analysis: '🔬', dataset_download_start: '📥', dataset_download_complete: '✅',
    dataset_clean: '🧹', dataset_preprocess: '⚙️', model_build: '🏗️',
    training_start: '🚀', training_complete: '🏆', profile_update: '👤',
    '2fa_setup_complete': '🛡️', dataset_analysis: '🔍',
  };

  if (loading) {
    return <div className="loading-overlay"><div className="spinner" /><p>Loading dashboard...</p></div>;
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Overview of your RGB-Pose Hub activity and system status</p>
      </div>
      <div className="page-body">
        {/* Stats Grid */}
        <div className="stats-grid" style={{ marginBottom: '1.5rem' }}>
          <div className="stat-card">
            <div className="stat-icon blue">🔬</div>
            <div className="stat-info">
              <h4>{stats?.total_analyses || 0}</h4>
              <p>Total Analyses</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon emerald">📤</div>
            <div className="stat-info">
              <h4>{stats?.total_uploads || 0}</h4>
              <p>Images Uploaded</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon amber">🗂️</div>
            <div className="stat-info">
              <h4>{datasetStatus?.total_images || 0}</h4>
              <p>Dataset Objects</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon purple">🔐</div>
            <div className="stat-info">
              <h4>{stats?.active_sessions || 0}</h4>
              <p>Active Sessions</p>
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          {/* Recent Activity */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">📋 Recent Activity</h3>
            </div>
            {recentActivity.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No activity yet. Start by uploading an image!</p>
            ) : (
              <div className="activity-feed">
                {recentActivity.map((item) => (
                  <div className="activity-item" key={item.id}>
                    <div className={`activity-dot ${item.category}`} />
                    <div>
                      <p>{actionIcons[item.action] || '📌'} {item.description || item.action.replace(/_/g, ' ')}</p>
                      <span className="activity-time">{formatTime(item.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* System Status */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">⚡ System Status</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.6rem 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Dataset</span>
                <span className={`badge ${datasetStatus?.status === 'ready' ? 'badge-success' : 'badge-warning'}`}>
                  {datasetStatus?.status === 'ready' ? `✓ ${datasetStatus.total_images} objects` : '○ Not loaded'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.6rem 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>ML Model</span>
                <span className={`badge ${modelStatus?.model?.model_exists ? 'badge-success' : 'badge-info'}`}>
                  {modelStatus?.model?.model_exists ? '✓ Trained' : '○ Similarity mode'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.6rem 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Model Accuracy</span>
                <span className="badge badge-purple">
                  {modelStatus?.training_summary?.final_val_accuracy
                    ? `${(modelStatus.training_summary.final_val_accuracy * 100).toFixed(1)}%`
                    : 'N/A'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.6rem 0' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Member Since</span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  {stats?.member_since ? new Date(stats.member_since).toLocaleDateString() : 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
