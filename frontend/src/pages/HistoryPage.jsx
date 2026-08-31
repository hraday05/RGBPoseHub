import { useState, useEffect } from 'react';
import { authAPI } from '../services/api';

export default function HistoryPage() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [category, setCategory] = useState('');

  useEffect(() => {
    loadHistory();
  }, [page, category]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const params = { page, per_page: 15 };
      if (category) params.category = category;
      const res = await authAPI.getHistory(params);
      setHistory(res.data.history || []);
      setTotalPages(res.data.pages || 1);
      setTotal(res.data.total || 0);
    } catch (err) {
      console.error('History load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDateTime = (iso) => {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleString('en-IN', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  };

  const categoryBadge = (cat) => {
    const map = {
      auth: { class: 'badge-info', icon: '🔐' },
      data: { class: 'badge-success', icon: '📊' },
      ml: { class: 'badge-warning', icon: '🧠' },
      system: { class: 'badge-purple', icon: '⚙️' },
    };
    const info = map[cat] || { class: 'badge-info', icon: '📌' };
    return <span className={`badge ${info.class}`}>{info.icon} {cat}</span>;
  };

  const statusBadge = (status) => {
    if (status === 'success') return <span className="badge badge-success">✓ Success</span>;
    if (status === 'failure') return <span className="badge badge-danger">✗ Failed</span>;
    return <span className="badge badge-warning">⏳ Pending</span>;
  };

  const categories = ['', 'auth', 'data', 'ml', 'system'];

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Activity History</h2>
        <p>Complete chronological log of all your actions on RGB-Pose Hub</p>
      </div>
      <div className="page-body">
        {/* Filters */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {categories.map((cat) => (
              <button key={cat || 'all'}
                className={`btn btn-sm ${category === cat ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => { setCategory(cat); setPage(1); }}>
                {cat ? cat.charAt(0).toUpperCase() + cat.slice(1) : 'All'}
              </button>
            ))}
          </div>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            {total} total entries
          </span>
        </div>

        {loading ? (
          <div className="loading-overlay"><div className="spinner" /><p>Loading history...</p></div>
        ) : history.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
            <p style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📭</p>
            <p style={{ color: 'var(--text-secondary)' }}>No activity recorded yet.</p>
          </div>
        ) : (
          <>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Action</th>
                    <th>Category</th>
                    <th>Description</th>
                    <th>Status</th>
                    <th>IP</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((item) => (
                    <tr key={item.id}>
                      <td style={{ whiteSpace: 'nowrap', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                        {formatDateTime(item.created_at)}
                      </td>
                      <td>
                        <span style={{ fontWeight: 500, fontSize: '0.88rem' }}>
                          {item.action.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td>{categoryBadge(item.category)}</td>
                      <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                        {item.description || '—'}
                      </td>
                      <td>{statusBadge(item.status)}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        {item.ip_address || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="pagination">
                <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
                {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                  let p;
                  if (totalPages <= 7) p = i + 1;
                  else if (page <= 4) p = i + 1;
                  else if (page >= totalPages - 3) p = totalPages - 6 + i;
                  else p = page - 3 + i;
                  return (
                    <button key={p} className={page === p ? 'active' : ''} onClick={() => setPage(p)}>
                      {p}
                    </button>
                  );
                })}
                <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
