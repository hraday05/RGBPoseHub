import { useState, useEffect } from 'react';
import { dataAPI } from '../services/api';

export default function DatasetPage() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [cleaning, setCleaning] = useState(false);
  const [preprocessing, setPreprocessing] = useState(false);
  const [cleanReport, setCleanReport] = useState(null);
  const [preprocessResult, setPreprocessResult] = useState(null);
  const [message, setMessage] = useState('');

  useEffect(() => { loadStatus(); }, []);

  const loadStatus = async () => {
    setLoading(true);
    try {
      const res = await dataAPI.getStatus();
      setStatus(res.data.dataset);
    } catch { setStatus(null); }
    finally { setLoading(false); }
  };

  const handleDownload = async () => {
    setDownloading(true);
    setMessage('');
    try {
      const res = await dataAPI.downloadDataset();
      setMessage(res.data.message);
      loadStatus();
    } catch (err) {
      setMessage('Download failed: ' + (err.response?.data?.error || err.message));
    } finally {
      setDownloading(false);
    }
  };

  const handleClean = async () => {
    setCleaning(true);
    try {
      const res = await dataAPI.cleanDataset({ remove_invalid: false });
      setCleanReport(res.data.report);
    } catch (err) {
      setMessage('Cleaning failed: ' + (err.response?.data?.error || err.message));
    } finally {
      setCleaning(false);
    }
  };

  const handlePreprocess = async () => {
    setPreprocessing(true);
    try {
      const res = await dataAPI.preprocessDataset({ augmentation_factor: 5 });
      setPreprocessResult(res.data.results);
    } catch (err) {
      setMessage('Preprocessing failed: ' + (err.response?.data?.error || err.message));
    } finally {
      setPreprocessing(false);
    }
  };

  if (loading) {
    return <div className="loading-overlay"><div className="spinner" /><p>Loading dataset status...</p></div>;
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Dataset Management</h2>
        <p>Download, clean, and preprocess the CLUBS dataset for model training</p>
      </div>
      <div className="page-body">
        {message && <div className="alert alert-info">ℹ {message}</div>}

        {/* Pipeline Steps */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
          {/* Step 1: Download */}
          <div className="card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>📥</div>
            <h4 style={{ marginBottom: '0.5rem' }}>Step 1: Download</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
              Fetch 85 object images from the CLUBS dataset on GitHub
            </p>
            {status?.status === 'ready' ? (
              <span className="badge badge-success" style={{ fontSize: '0.85rem', padding: '0.35rem 0.85rem' }}>
                ✅ {status.total_images} images loaded
              </span>
            ) : (
              <button className="btn btn-primary btn-sm" onClick={handleDownload} disabled={downloading}>
                {downloading ? <><span className="spinner" /> Downloading...</> : '📥 Download Dataset'}
              </button>
            )}
          </div>

          {/* Step 2: Clean */}
          <div className="card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>🧹</div>
            <h4 style={{ marginBottom: '0.5rem' }}>Step 2: Clean</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
              Validate images, check for corruption, find duplicates
            </p>
            <button className="btn btn-primary btn-sm" onClick={handleClean}
              disabled={cleaning || status?.status !== 'ready'}>
              {cleaning ? <><span className="spinner" /> Cleaning...</> : '🧹 Run Cleaner'}
            </button>
          </div>

          {/* Step 3: Preprocess */}
          <div className="card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>⚙️</div>
            <h4 style={{ marginBottom: '0.5rem' }}>Step 3: Preprocess</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
              Resize to 224×224, normalize, apply data augmentation (5x)
            </p>
            <button className="btn btn-primary btn-sm" onClick={handlePreprocess}
              disabled={preprocessing || status?.status !== 'ready'}>
              {preprocessing ? <><span className="spinner" /> Processing...</> : '⚙️ Preprocess'}
            </button>
          </div>
        </div>

        {/* Clean Report */}
        {cleanReport && (
          <div className="card slide-up" style={{ marginBottom: '1.5rem' }}>
            <h4 style={{ marginBottom: '1rem' }}>🧹 Cleaning Report</h4>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-icon blue">📋</div>
                <div className="stat-info"><h4>{cleanReport.total_scanned}</h4><p>Total Scanned</p></div>
              </div>
              <div className="stat-card">
                <div className="stat-icon emerald">✓</div>
                <div className="stat-info"><h4>{cleanReport.valid}</h4><p>Valid Images</p></div>
              </div>
              <div className="stat-card">
                <div className="stat-icon red">✗</div>
                <div className="stat-info"><h4>{cleanReport.corrupted}</h4><p>Issues Found</p></div>
              </div>
              <div className="stat-card">
                <div className="stat-icon amber">📎</div>
                <div className="stat-info"><h4>{cleanReport.duplicates}</h4><p>Duplicates</p></div>
              </div>
            </div>
          </div>
        )}

        {/* Preprocess Result */}
        {preprocessResult && (
          <div className="card slide-up">
            <h4 style={{ marginBottom: '1rem' }}>⚙️ Preprocessing Results</h4>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-icon blue">🖼️</div>
                <div className="stat-info"><h4>{preprocessResult.total_original}</h4><p>Original Images</p></div>
              </div>
              <div className="stat-card">
                <div className="stat-icon emerald">✨</div>
                <div className="stat-info"><h4>{preprocessResult.total_processed}</h4><p>Processed</p></div>
              </div>
              <div className="stat-card">
                <div className="stat-icon purple">🔄</div>
                <div className="stat-info"><h4>{preprocessResult.total_augmented}</h4><p>Augmented</p></div>
              </div>
              <div className="stat-card">
                <div className="stat-icon amber">📊</div>
                <div className="stat-info">
                  <h4>{Object.keys(preprocessResult.classes || {}).length}</h4><p>Classes</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Dataset Info */}
        {status?.status === 'ready' && (
          <div className="card" style={{ marginTop: '1.5rem' }}>
            <h4 style={{ marginBottom: '0.75rem' }}>📊 Dataset Overview</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Total Images</span>
                <p style={{ fontSize: '1.2rem', fontWeight: 600 }}>{status.total_images}</p>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Total Size</span>
                <p style={{ fontSize: '1.2rem', fontWeight: 600 }}>{status.total_size_mb} MB</p>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Source</span>
                <p style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--accent-blue)' }}>CLUBS Benchmark</p>
              </div>
            </div>
            {status.sample_objects && (
              <div style={{ marginTop: '1rem' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Sample Objects</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.4rem' }}>
                  {status.sample_objects.map((name, i) => (
                    <span key={i} className="badge badge-info">{name}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
