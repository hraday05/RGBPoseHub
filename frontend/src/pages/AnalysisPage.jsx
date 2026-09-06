import { useState, useRef, useEffect } from 'react';
import { dataAPI, mlAPI } from '../services/api';

export default function AnalysisPage() {
  const [tab, setTab] = useState('upload'); // upload | catalog
  const [sherloqCategory, setSherloqCategory] = useState('gatekeeper'); 
  // gatekeeper | general | metadata | inspection | colors | detail | noise | jpeg

  // Inspection Tool Controls
  const [activeBitPlane, setActiveBitPlane] = useState(0);
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [magnifierPos, setMagnifierPos] = useState({ x: 50, y: 50, show: false });

  // State
  const [dragover, setDragover] = useState(false);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [poseLoading, setPoseLoading] = useState(false);
  const [error, setError] = useState('');

  // Sample RGB-D State
  const [samples, setSamples] = useState([]);
  const [samplesLoading, setSamplesLoading] = useState(false);

  const [forensics, setForensics] = useState(null);
  const [poseResults, setPoseResults] = useState(null);
  const [currentFilename, setCurrentFilename] = useState(null);

  // Catalog State
  const [objects, setObjects] = useState([]);
  const [catalogLoading, setCatalogLoading] = useState(false);

  const fileInputRef = useRef(null);

  useEffect(() => {
    loadSamples();
    if (tab === 'catalog') loadCatalog();
  }, [tab]);

  const loadSamples = async () => {
    setSamplesLoading(true);
    try {
      const res = await mlAPI.getSampleRGBDImages();
      setSamples(res.data.samples || []);
    } catch {
      setSamples([]);
    } finally {
      setSamplesLoading(false);
    }
  };

  const loadCatalog = async () => {
    setCatalogLoading(true);
    try {
      const res = await dataAPI.listObjects();
      setObjects(res.data.objects || []);
    } catch {
      setObjects([]);
    } finally {
      setCatalogLoading(false);
    }
  };

  const handleForensicAnalysis = async (file, depthFile = null) => {
    if (!file || !file.type.startsWith('image/')) {
      setError('Please select a valid image file');
      return;
    }
    setError('');
    setForensics(null);
    setPoseResults(null);

    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(file);

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('image', file);
      if (depthFile) formData.append('depth_image', depthFile);

      const res = await mlAPI.forensicAnalyze(formData);
      setForensics(res.data.forensics);
      setCurrentFilename(res.data.filename);
      if (res.data.original_image && !preview) {
        setPreview(`data:image/png;base64,${res.data.original_image}`);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Forensic analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const analyzeFilename = async (filename) => {
    setLoading(true);
    setError('');
    setForensics(null);
    setPoseResults(null);
    setTab('upload');
    try {
      const res = await mlAPI.forensicAnalyzeJson({ filename });
      setForensics(res.data.forensics);
      setCurrentFilename(filename);
      if (res.data.original_image) {
        setPreview(`data:image/png;base64,${res.data.original_image}`);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const proceedToPoseEstimation = async () => {
    if (!currentFilename || !forensics?.rgbd_gatekeeper?.is_rgbd) return;

    setPoseLoading(true);
    setError('');
    try {
      const res = await mlAPI.estimatePose({
        filename: currentFilename,
        depth_stats: forensics.rgbd_gatekeeper.depth_stats,
      });
      setPoseResults(res.data.pose_result);
    } catch (err) {
      setError(err.response?.data?.error || 'Pose estimation failed');
    } finally {
      setPoseLoading(false);
    }
  };

  const resetAnalysis = () => {
    setForensics(null);
    setPoseResults(null);
    setPreview(null);
    setCurrentFilename(null);
    setError('');
  };

  const gatekeeper = forensics?.rgbd_gatekeeper;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Sherloq Image Forensics & 6D Pose Estimation Hub</h2>
        <p>Multi-category forensic inspection workbench with heatmaps, bit-planes, EXIF, and RGB-D 6D pose estimation</p>
      </div>

      <div className="page-body">
        {/* Main Tab Switcher */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
          <button
            className={`btn ${tab === 'upload' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
            onClick={() => setTab('upload')}
          >
            📤 Upload Image / RGB-D
          </button>
          <button
            className={`btn ${tab === 'catalog' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
            onClick={() => setTab('catalog')}
          >
            🗂️ CLUBS Catalog
          </button>
        </div>

        {error && <div className="alert alert-error">⚠ {error}</div>}

        {/* Upload Tab */}
        {tab === 'upload' && (
          <>
            {!forensics && !loading && (
              <>
                <div
                  className={`upload-zone ${dragover ? 'dragover' : ''}`}
                  onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
                  onDragLeave={() => setDragover(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragover(false);
                    if (e.dataTransfer.files[0]) handleForensicAnalysis(e.dataTransfer.files[0]);
                  }}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="upload-icon">🔬</div>
                  <p><strong>Drop an image or RGB-D file here</strong> or click to browse</p>
                  <p className="upload-hint">Supports PNG, JPG, TIFF, 4-Channel RGBD • Max 16MB</p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    hidden
                    onChange={(e) => e.target.files[0] && handleForensicAnalysis(e.target.files[0])}
                  />
                </div>

                {/* Sample RGB-D Test Images Section */}
                <div style={{ marginTop: '1.5rem', padding: '1.25rem', background: 'var(--code-bg)', borderRadius: '12px', border: '1px solid var(--border)' }}>
                  <h4 style={{ margin: '0 0 0.5rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span>🧪</span> Try Sample Verified RGB-D Images (1-Click Test)
                  </h4>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                    Click any sample below to load a pre-generated 4-channel RGB-D image and verify depth gatekeeper + 6D pose estimation:
                  </p>

                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    {samples.map((s) => (
                      <button
                        key={s.filename}
                        className="btn btn-secondary btn-sm"
                        style={{ border: '1px solid #10b981', color: '#10b981', background: 'rgba(16, 185, 129, 0.1)' }}
                        onClick={() => analyzeFilename(s.filename)}
                      >
                        📷 {s.name} ({s.type})
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            {loading && (
              <div className="loading-overlay">
                <div className="spinner" />
                <p>Running Sherloq Multi-Category Forensic Inspection & Depth Gatekeeper...</p>
              </div>
            )}

            {/* Forensics Analysis Workbench */}
            {forensics && (
              <div className="slide-up">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3>Part 1: Sherloq Multi-Category Forensic Workbench</h3>
                  <button className="btn btn-secondary btn-sm" onClick={resetAnalysis}>
                    🔄 New Inspection
                  </button>
                </div>

                {/* Gatekeeper Banner */}
                <div
                  style={{
                    padding: '1.25rem',
                    borderRadius: '12px',
                    marginBottom: '1.5rem',
                    background: gatekeeper?.is_rgbd ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                    border: `1.5px solid ${gatekeeper?.is_rgbd ? '#10b981' : '#ef4444'}`,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.4rem' }}>
                        <span style={{ fontSize: '1.25rem', fontWeight: 'bold', color: gatekeeper?.is_rgbd ? '#10b981' : '#ef4444' }}>
                          {gatekeeper?.is_rgbd ? '✅ VERIFIED RGB-D IMAGE' : '❌ STOPPED AT GATEKEEPER: NOT AN RGB-D IMAGE'}
                        </span>
                        <span className="badge" style={{ background: gatekeeper?.is_rgbd ? '#10b98122' : '#ef444422', color: gatekeeper?.is_rgbd ? '#10b981' : '#ef4444' }}>
                          {gatekeeper?.status}
                        </span>
                      </div>
                      <p style={{ margin: 0, fontSize: '0.92rem', color: 'var(--text-secondary)' }}>
                        {gatekeeper?.reason}
                      </p>
                      {gatekeeper?.is_rgbd && gatekeeper?.depth_stats && (
                        <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', fontSize: '0.85rem' }}>
                          <span><strong>Coverage:</strong> {gatekeeper.depth_stats.coverage_pct}%</span>
                          <span><strong>Depth Range:</strong> {gatekeeper.depth_stats.min_depth}m – {gatekeeper.depth_stats.max_depth}m</span>
                          <span><strong>Mean Depth:</strong> {gatekeeper.depth_stats.mean_depth}m</span>
                        </div>
                      )}
                    </div>

                    <div>
                      {gatekeeper?.is_rgbd ? (
                        <button className="btn btn-primary" onClick={proceedToPoseEstimation} disabled={poseLoading}>
                          {poseLoading ? 'Computing 6D Pose...' : '➡️ Proceed to 6D Pose Detection'}
                        </button>
                      ) : (
                        <div style={{ textAlign: 'right' }}>
                          <button className="btn btn-secondary" disabled style={{ opacity: 0.6, cursor: 'not-allowed' }}>
                            🚫 Pose Detection Blocked
                          </button>
                          <div style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '0.25rem' }}>
                            Requires Depth Data
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Sherloq Category Navigation Bar */}
                <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', borderBottom: '1px solid var(--border)', marginBottom: '1.25rem', paddingBottom: '0.5rem' }}>
                  <button className={`btn btn-sm ${sherloqCategory === 'gatekeeper' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSherloqCategory('gatekeeper')}>
                    📏 Depth Map Heatmap
                  </button>
                  <button className={`btn btn-sm ${sherloqCategory === 'general' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSherloqCategory('general')}>
                    🧰 General & Hashes
                  </button>
                  <button className={`btn btn-sm ${sherloqCategory === 'metadata' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSherloqCategory('metadata')}>
                    📋 EXIF & GPS
                  </button>
                  <button className={`btn btn-sm ${sherloqCategory === 'inspection' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSherloqCategory('inspection')}>
                    🔍 Enhancing Magnifier
                  </button>
                  <button className={`btn btn-sm ${sherloqCategory === 'colors' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSherloqCategory('colors')}>
                    🎨 Colors & PCA
                  </button>
                  <button className={`btn btn-sm ${sherloqCategory === 'detail' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSherloqCategory('detail')}>
                    🌊 Detail & Filters
                  </button>
                  <button className={`btn btn-sm ${sherloqCategory === 'noise' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSherloqCategory('noise')}>
                    🧱 Noise & Bit Planes
                  </button>
                  <button className={`btn btn-sm ${sherloqCategory === 'jpeg' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSherloqCategory('jpeg')}>
                    🛡️ JPEG & Tampering
                  </button>
                </div>

                {/* Depth Heatmap Tab */}
                {sherloqCategory === 'gatekeeper' && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
                    <div className="card">
                      <h4>Original RGB Input</h4>
                      <img src={preview} alt="RGB" style={{ width: '100%', borderRadius: '8px', marginTop: '0.5rem' }} />
                    </div>
                    <div className="card">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h4>Depth Map Visualization (Inferno Heatmap)</h4>
                        <span className="badge badge-success">0.4m – 2.0m Scale</span>
                      </div>
                      {gatekeeper?.depth_heatmap ? (
                        <div style={{ marginTop: '0.5rem' }}>
                          <img src={`data:image/png;base64,${gatekeeper.depth_heatmap}`} alt="Depth Heatmap" style={{ width: '100%', borderRadius: '8px' }} />
                          {/* Color bar scale */}
                          <div style={{ marginTop: '0.5rem', height: '12px', background: 'linear-gradient(to right, #000000, #ff0000, #ffaa00, #ffff00)', borderRadius: '6px' }} />
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                            <span>Close (0.4m)</span>
                            <span>Mid (1.2m)</span>
                            <span>Far (2.0m+)</span>
                          </div>
                        </div>
                      ) : (
                        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                          <p style={{ fontSize: '2rem' }}>🚫</p>
                          <p>No depth map detected in standard 2D image.</p>
                          <p style={{ fontSize: '0.85rem', color: '#10b981', marginTop: '0.5rem' }}>
                            💡 Click "Try Sample Verified RGB-D Images" above to test depth heatmaps!
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Category 1: General & Digest */}
                {sherloqCategory === 'general' && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
                    <div className="card">
                      <h4>Physical File Digest</h4>
                      <table className="info-table" style={{ width: '100%', marginTop: '0.75rem', fontSize: '0.9rem' }}>
                        <tbody>
                          <tr><td><strong>Format</strong></td><td>{forensics.metadata.format}</td></tr>
                          <tr><td><strong>Dimensions</strong></td><td>{forensics.metadata.dimensions}</td></tr>
                          <tr><td><strong>Megapixels</strong></td><td>{forensics.metadata.megapixels} MP</td></tr>
                          <tr><td><strong>Color Mode</strong></td><td>{forensics.metadata.color_mode}</td></tr>
                          <tr><td><strong>Channels</strong></td><td>{forensics.metadata.channels}</td></tr>
                          <tr><td><strong>Bit Depth</strong></td><td>{forensics.metadata.bit_depth}</td></tr>
                          <tr><td><strong>File Size</strong></td><td>{forensics.metadata.file_size_formatted}</td></tr>
                        </tbody>
                      </table>
                    </div>

                    <div className="card">
                      <h4>Cryptographic & Perceptual Hashes</h4>
                      <div style={{ fontSize: '0.85rem' }}>
                        <p style={{ marginBottom: '0.3rem' }}><strong>MD5:</strong></p>
                        <code style={{ wordBreak: 'break-all', display: 'block', padding: '0.4rem', marginBottom: '0.6rem' }}>{forensics.hashes.md5}</code>
                        <p style={{ marginBottom: '0.3rem' }}><strong>SHA-1:</strong></p>
                        <code style={{ wordBreak: 'break-all', display: 'block', padding: '0.4rem', marginBottom: '0.6rem' }}>{forensics.hashes.sha1}</code>
                        <p style={{ marginBottom: '0.3rem' }}><strong>SHA-256:</strong></p>
                        <code style={{ wordBreak: 'break-all', display: 'block', padding: '0.4rem', marginBottom: '0.6rem' }}>{forensics.hashes.sha256}</code>
                        <p style={{ marginBottom: '0.3rem' }}><strong>Difference Hash (dHash):</strong></p>
                        <code style={{ wordBreak: 'break-all', display: 'block', padding: '0.4rem', color: '#10b981' }}>{forensics.hashes.dhash}</code>
                      </div>
                    </div>

                    <div className="card" style={{ gridColumn: '1 / -1' }}>
                      <h4>Raw Hex Byte Viewer (First 256 Bytes)</h4>
                      <div style={{ maxHeight: '200px', overflowY: 'auto', background: 'var(--code-bg)', padding: '0.75rem', borderRadius: '8px', fontFamily: 'var(--mono)', fontSize: '0.8rem' }}>
                        {forensics.hex_dump?.rows?.map((row, i) => (
                          <div key={i} style={{ display: 'flex', gap: '1.5rem' }}>
                            <span style={{ color: '#3b82f6' }}>{row.offset}</span>
                            <span style={{ color: '#f59e0b' }}>{row.hex}</span>
                            <span style={{ color: '#10b981' }}>{row.ascii}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Category 2: EXIF & Geolocation */}
                {sherloqCategory === 'metadata' && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
                    <div className="card">
                      <h4>EXIF Full Metadata Scan ({forensics.exif.tags_count} tags)</h4>
                      <div style={{ maxHeight: '350px', overflowY: 'auto', background: 'var(--code-bg)', padding: '0.75rem', borderRadius: '8px', fontSize: '0.85rem' }}>
                        {Object.entries(forensics.exif.data).map(([k, v]) => (
                          <div key={k} style={{ marginBottom: '0.4rem', borderBottom: '1px dashed var(--border)', paddingBottom: '0.25rem' }}>
                            <strong style={{ color: '#3b82f6' }}>{k}:</strong> {String(v)}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="card">
                      <h4>GPS Geolocation Information</h4>
                      {forensics.exif.gps?.has_location ? (
                        <div style={{ padding: '1rem', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '8px', border: '1px solid #10b981' }}>
                          <p style={{ fontWeight: 'bold', fontSize: '1.1rem', color: '#10b981' }}>📍 GPS Location Found</p>
                          <p style={{ margin: '0.5rem 0' }}><strong>Coordinates:</strong> {forensics.exif.gps.formatted}</p>
                          <a href={forensics.exif.gps.maps_link} target="_blank" rel="noreferrer" className="btn btn-primary btn-sm" style={{ marginTop: '0.5rem' }}>
                            🌐 View on Google Maps
                          </a>
                        </div>
                      ) : (
                        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                          <p style={{ fontSize: '2rem' }}>🌐</p>
                          <p>No embedded GPS coordinates found in file header.</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Category 3: Enhancing Magnifier */}
                {sherloqCategory === 'inspection' && (
                  <div className="card">
                    <h4>Interactive Enhancing Magnifier & Global Adjustments</h4>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                      Hover over image to activate digital magnifying lens. Adjust brightness & contrast in real-time.
                    </p>

                    <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                      <div>
                        <label style={{ fontSize: '0.85rem' }}>Brightness: {brightness}%</label>
                        <input type="range" min="50" max="200" value={brightness} onChange={(e) => setBrightness(e.target.value)} style={{ display: 'block' }} />
                      </div>
                      <div>
                        <label style={{ fontSize: '0.85rem' }}>Contrast: {contrast}%</label>
                        <input type="range" min="50" max="200" value={contrast} onChange={(e) => setContrast(e.target.value)} style={{ display: 'block' }} />
                      </div>
                      <button className="btn btn-secondary btn-sm" onClick={() => { setBrightness(100); setContrast(100); }}>Reset Filters</button>
                    </div>

                    <div
                      style={{ position: 'relative', overflow: 'hidden', borderRadius: '8px', cursor: 'crosshair', display: 'inline-block' }}
                      onMouseMove={(e) => {
                        const rect = e.currentTarget.getBoundingClientRect();
                        const x = ((e.clientX - rect.left) / rect.width) * 100;
                        const y = ((e.clientY - rect.top) / rect.height) * 100;
                        setMagnifierPos({ x, y, show: true });
                      }}
                      onMouseLeave={() => setMagnifierPos((prev) => ({ ...prev, show: false }))}
                    >
                      <img
                        src={preview}
                        alt="Magnifier Target"
                        style={{
                          maxWidth: '100%',
                          filter: `brightness(${brightness}%) contrast(${contrast}%)`,
                          display: 'block',
                        }}
                      />
                      {magnifierPos.show && (
                        <div
                          style={{
                            position: 'absolute',
                            left: `${magnifierPos.x}%`,
                            top: `${magnifierPos.y}%`,
                            width: '140px',
                            height: '140px',
                            borderRadius: '50%',
                            border: '3px solid #10b981',
                            transform: 'translate(-50%, -50%)',
                            pointerEvents: 'none',
                            backgroundImage: `url(${preview})`,
                            backgroundPosition: `${magnifierPos.x}% ${magnifierPos.y}%`,
                            backgroundSize: '300%',
                            boxShadow: '0 0 15px rgba(0,0,0,0.6)',
                          }}
                        />
                      )}
                    </div>
                  </div>
                )}

                {/* Category 4: Colors & PCA */}
                {sherloqCategory === 'colors' && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
                    <div className="card">
                      <h4>Color Space Conversions (HSV, YCbCr, Gray)</h4>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginTop: '0.75rem' }}>
                        <div>
                          <p style={{ fontSize: '0.8rem', textAlign: 'center', marginBottom: '0.25rem' }}>HSV Color Space</p>
                          {forensics.color_spaces?.hsv && <img src={`data:image/png;base64,${forensics.color_spaces.hsv}`} alt="HSV" style={{ width: '100%', borderRadius: '6px' }} />}
                        </div>
                        <div>
                          <p style={{ fontSize: '0.8rem', textAlign: 'center', marginBottom: '0.25rem' }}>YCbCr Luminance/Chroma</p>
                          {forensics.color_spaces?.ycbcr && <img src={`data:image/png;base64,${forensics.color_spaces.ycbcr}`} alt="YCbCr" style={{ width: '100%', borderRadius: '6px' }} />}
                        </div>
                      </div>
                    </div>

                    <div className="card">
                      <h4>PCA Color Component Projection Heatmap</h4>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                        Projects pixel colors onto 1st principal component to expose subtle color inconsistencies.
                      </p>
                      {forensics.pca_projection?.pca_heatmap && (
                        <img src={`data:image/png;base64,${forensics.pca_projection.pca_heatmap}`} alt="PCA Projection" style={{ width: '100%', borderRadius: '8px' }} />
                      )}
                      {forensics.pca_projection?.explained_variance_pct && (
                        <div style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
                          <strong>Explained Variance Ratio:</strong> PC1={forensics.pca_projection.explained_variance_pct[0]}% | PC2={forensics.pca_projection.explained_variance_pct[1]}%
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Category 5: Detail & Spatial Filters */}
                {sherloqCategory === 'detail' && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
                    <div className="card">
                      <h4>Echo Edge Filter (Derivative Sobel)</h4>
                      {forensics.detail_filters?.echo_edges && <img src={`data:image/png;base64,${forensics.detail_filters.echo_edges}`} alt="Echo Edges" style={{ width: '100%', borderRadius: '8px' }} />}
                    </div>

                    <div className="card">
                      <h4>Luminance Gradient Heatmap</h4>
                      {forensics.detail_filters?.luminance_gradient && <img src={`data:image/png;base64,${forensics.detail_filters.luminance_gradient}`} alt="Luminance Gradient" style={{ width: '100%', borderRadius: '8px' }} />}
                    </div>

                    <div className="card">
                      <h4>High-Frequency Split (Details)</h4>
                      {forensics.detail_filters?.high_frequency && <img src={`data:image/png;base64,${forensics.detail_filters.high_frequency}`} alt="High Frequency" style={{ width: '100%', borderRadius: '8px' }} />}
                    </div>
                  </div>
                )}

                {/* Category 6: Noise & Bit Planes */}
                {sherloqCategory === 'noise' && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
                    <div className="card">
                      <h4>Interactive 8 Bit-Plane Slicer</h4>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                        Select bit plane (Bit 0 LSB reveals hidden noise/steganography; Bit 7 MSB shows structural outline).
                      </p>
                      <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
                        {[0, 1, 2, 3, 4, 5, 6, 7].map((b) => (
                          <button key={b} className={`btn btn-sm ${activeBitPlane === b ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveBitPlane(b)}>
                            Bit {b} {b === 0 ? '(LSB)' : b === 7 ? '(MSB)' : ''}
                          </button>
                        ))}
                      </div>
                      {forensics.bit_planes?.[`bit_${activeBitPlane}`] && (
                        <img src={`data:image/png;base64,${forensics.bit_planes[`bit_${activeBitPlane}`]}`} alt={`Bit ${activeBitPlane}`} style={{ width: '100%', borderRadius: '8px' }} />
                      )}
                    </div>

                    <div className="card">
                      <h4>Block Min/Max Deviation Noise Map</h4>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                        Highlights local 8x8 block noise variance to pinpoint spliced regions.
                      </p>
                      {forensics.quality_analysis?.block_deviation_map && (
                        <img src={`data:image/png;base64,${forensics.quality_analysis.block_deviation_map}`} alt="Block Noise Map" style={{ width: '100%', borderRadius: '8px' }} />
                      )}
                    </div>
                  </div>
                )}

                {/* Category 7: JPEG & Tampering */}
                {sherloqCategory === 'jpeg' && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
                    <div className="card">
                      <h4>Sherloq Error Level Analysis (ELA) Heatmap</h4>
                      {forensics.ela_heatmap && <img src={`data:image/png;base64,${forensics.ela_heatmap}`} alt="ELA Heatmap" style={{ width: '100%', borderRadius: '8px' }} />}
                    </div>

                    <div className="card">
                      <h4>JPEG Quality & Contrast Tampering Assessment</h4>
                      <table className="info-table" style={{ width: '100%', marginTop: '0.75rem', fontSize: '0.9rem' }}>
                        <tbody>
                          <tr><td><strong>Est. JPEG Quality Factor</strong></td><td>{forensics.jpeg_info?.estimated_jpeg_quality}%</td></tr>
                          <tr><td><strong>Contrast Comb Artifacts</strong></td><td>{forensics.jpeg_info?.has_contrast_comb_gaps ? '⚠️ Detected (Comb Gaps)' : 'None (Smooth)'}</td></tr>
                          <tr><td><strong>Tampering Verdict</strong></td><td><span className="badge badge-info">{forensics.jpeg_info?.tampering_assessment}</span></td></tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Part 2: 6D Pose Estimation Results */}
                {poseResults && (
                  <div style={{ marginTop: '2rem', borderTop: '2px dashed #10b981', paddingTop: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                      <span style={{ fontSize: '1.5rem' }}>🎯</span>
                      <h3>Part 2: 6D Pose Detection & Object Estimation Results</h3>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
                      <div className="card">
                        <h4>3D Pose Visualization Overlay</h4>
                        <img src={`data:image/png;base64,${poseResults.pose_visualization}`} alt="3D Pose Overlay" style={{ width: '100%', borderRadius: '8px' }} />
                      </div>

                      <div className="card">
                        <h4>6D Pose Parameters & Spatial Metrics</h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem' }}>
                          <div style={{ background: 'var(--code-bg)', padding: '0.75rem', borderRadius: '8px' }}>
                            <h5 style={{ margin: '0 0 0.25rem', color: '#3b82f6' }}>Target Object & Confidence</h5>
                            <div style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>{poseResults.object_name}</div>
                            <div style={{ fontSize: '0.85rem', color: '#10b981' }}>Confidence: {poseResults.confidence_pct}%</div>
                          </div>

                          <div style={{ background: 'var(--code-bg)', padding: '0.75rem', borderRadius: '8px' }}>
                            <h5 style={{ margin: '0 0 0.25rem', color: '#f59e0b' }}>3D Translation Vector (Tx, Ty, Tz)</h5>
                            <div style={{ fontFamily: 'var(--mono)', fontSize: '0.95rem' }}>{poseResults.translation_3d.vector_formatted}</div>
                          </div>

                          <div style={{ background: 'var(--code-bg)', padding: '0.75rem', borderRadius: '8px' }}>
                            <h5 style={{ margin: '0 0 0.25rem', color: '#8b5cf6' }}>3D Rotation & Quaternion</h5>
                            <div style={{ fontSize: '0.85rem' }}><strong>Euler:</strong> {poseResults.rotation_euler_deg.formatted}</div>
                            <div style={{ fontSize: '0.85rem', fontFamily: 'var(--mono)', marginTop: '0.2rem' }}>
                              <strong>Quaternion:</strong> {poseResults.rotation_quaternion.formatted}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
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
                  {objects.length} objects in CLUBS dataset. Click any object for Sherloq Multi-Category Forensics & Depth Gatekeeper analysis.
                </p>
                <div className="object-grid">
                  {objects.map((obj) => (
                    <div className="object-card" key={obj.id} onClick={() => analyzeFilename(obj.filename)}>
                      <img
                        src={dataAPI.getObjectImage(obj.filename)}
                        alt={obj.name}
                        loading="lazy"
                        onError={(e) => { e.target.style.background = '#1a1d27'; e.target.alt = 'Loading...'; }}
                      />
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
