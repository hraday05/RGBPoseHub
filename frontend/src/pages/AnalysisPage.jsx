import { useState, useRef, useEffect } from 'react';
import { dataAPI, mlAPI } from '../services/api';

const PREDICTION_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444'];

export default function AnalysisPage() {
  const [tab, setTab] = useState('upload'); // upload | catalog
  const [dragover, setDragover] = useState(false);
  const [preview, setPreview] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [objects, setObjects] = useState([]);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (tab === 'catalog') loadCatalog();
  }, [tab]);

  const loadCatalog = async () => {
    setCatalogLoading(true);
    try {
      const res = await dataAPI.listObjects();
      setObjects(res.data.objects || []);
    } catch { setObjects([]); }
    finally { setCatalogLoading(false); }
  };

  const handleFile = async (file) => {
    if (!file || !file.type.startsWith('image/')) {
      setError('Please select a valid image file');
      return;
    }
    setError('');
    setResults(null);

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(file);

    // Upload and analyze
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('image', file);
      const res = await mlAPI.predict(formData);
      setResults(res.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragover(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const analyzeDatasetImage = async (filename) => {
    setLoading(true);
    setError('');
    setResults(null);
    setTab('upload');
    try {
      const res = await mlAPI.predictDatasetImage(filename);
      setResults(res.data);
      if (res.data.original_image) {
        setPreview(`data:image/png;base64,${res.data.original_image}`);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Image Analysis</h2>
        <p>Upload an image or select from the CLUBS dataset for object classification</p>
      </div>
      <div className="page-body">
        {/* Tab Switcher */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
          <button className={`btn ${tab === 'upload' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
            onClick={() => setTab('upload')}>📤 Upload Image</button>
          <button className={`btn ${tab === 'catalog' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
            onClick={() => setTab('catalog')}>🗂️ CLUBS Catalog</button>
        </div>

        {error && <div className="alert alert-error">⚠ {error}</div>}

        {/* Upload Tab */}
        {tab === 'upload' && (
          <>
            {!results && !loading && (
              <div className={`upload-zone ${dragover ? 'dragover' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
                onDragLeave={() => setDragover(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}>
                <div className="upload-icon">📁</div>
                <p><strong>Drop an image here</strong> or click to browse</p>
                <p className="upload-hint">Supports PNG, JPG, JPEG • Max 16MB</p>
                <input ref={fileInputRef} type="file" accept="image/*" hidden
                  onChange={(e) => e.target.files[0] && handleFile(e.target.files[0])} />
              </div>
            )}

            {loading && (
              <div className="loading-overlay">
                <div className="spinner" />
                <p>Analyzing image... This may take a moment.</p>
              </div>
            )}

            {results && (
              <div className="slide-up">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3>Analysis Results</h3>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <span className={`badge ${results.results?.method === 'cnn_classifier' ? 'badge-success' : 'badge-info'}`}>
                      {results.results?.method === 'cnn_classifier' ? '🧠 CNN Model' : '📐 Similarity Match'}
                    </span>
                    <button className="btn btn-secondary btn-sm" onClick={() => { setResults(null); setPreview(null); }}>
                      🔄 New Analysis
                    </button>
                  </div>
                </div>

                <div className="results-panel">
                  {/* Original / Annotated Image */}
                  <div>
                    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                      <div className="result-image-container">
                        <img src={results.annotated_image ? `data:image/png;base64,${results.annotated_image}` : preview}
                          alt="Analysis result" />
                      </div>
                    </div>
                  </div>

                  {/* Predictions */}
                  <div>
                    <div className="card">
                      <h4 style={{ marginBottom: '1rem' }}>Top Predictions</h4>
                      <div className="prediction-list">
                        {results.results?.predictions?.map((pred, i) => (
                          <div className="prediction-item" key={i}>
                            <div className="prediction-rank"
                              style={{ background: `${PREDICTION_COLORS[i]}22`, color: PREDICTION_COLORS[i] }}>
                              #{i + 1}
                            </div>
                            <div className="prediction-bar">
                              <div className="prediction-bar-label">
                                <span style={{ fontWeight: 600 }}>{pred.class_name}</span>
                                <span style={{ color: PREDICTION_COLORS[i], fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                                  {pred.confidence_pct?.toFixed(1)}%
                                </span>
                              </div>
                              <div className="prediction-bar-track">
                                <div className="prediction-bar-fill"
                                  style={{ width: `${Math.min(pred.confidence_pct, 100)}%`, background: PREDICTION_COLORS[i] }} />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* Catalog Tab */}
        {tab === 'catalog' && (
          <div>
            {catalogLoading ? (
              <div className="loading-overlay"><div className="spinner" /><p>Loading CLUBS catalog...</p></div>
            ) : objects.length === 0 ? (
              <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                <p style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📦</p>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                  Dataset not loaded yet. Download it from the Dataset page first.
                </p>
              </div>
            ) : (
              <>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
                  {objects.length} objects in CLUBS dataset. Click any object to analyze it.
                </p>
                <div className="object-grid">
                  {objects.map((obj) => (
                    <div className="object-card" key={obj.id} onClick={() => analyzeDatasetImage(obj.filename)}>
                      <img src={dataAPI.getObjectImage(obj.filename)}
                        alt={obj.name} loading="lazy"
                        onError={(e) => { e.target.style.background = '#1a1d27'; e.target.alt = 'Loading...'; }} />
                      <div className="object-info">
                        <div className="object-name">{obj.name}</div>
                        <div className="object-id">#{obj.id}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
