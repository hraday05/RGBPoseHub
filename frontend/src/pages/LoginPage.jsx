import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api';

export default function LoginPage({ onLogin }) {
  const navigate = useNavigate();
  const [mode, setMode] = useState('login'); // login | register | 2fa-setup | 2fa-login
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({ email: '', username: '', password: '', full_name: '' });
  const [twoFAData, setTwoFAData] = useState(null);
  const [otpCode, setOtpCode] = useState(['', '', '', '', '', '']);
  const [pendingUserId, setPendingUserId] = useState(null);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError('');
  };

  const handleOtpChange = (index, value) => {
    if (value.length > 1) value = value.slice(-1);
    if (value && !/^\d$/.test(value)) return;
    const newOtp = [...otpCode];
    newOtp[index] = value;
    setOtpCode(newOtp);
    if (value && index < 5) {
      document.getElementById(`otp-${index + 1}`)?.focus();
    }
  };

  const handleOtpKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otpCode[index] && index > 0) {
      document.getElementById(`otp-${index - 1}`)?.focus();
    }
  };

  const getOtpString = () => otpCode.join('');

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await authAPI.register(formData);
      setTwoFAData(res.data.two_factor);
      setPendingUserId(res.data.user.id);
      setMode('2fa-setup');
    } catch (err) {
      const serverMsg = err.response?.data?.error || err.response?.data?.message || err.message;
      if (err.code === 'ERR_NETWORK') {
        setError('Cannot connect to backend server. Make sure Flask is running on port 5001.');
      } else {
        setError(serverMsg || 'Registration failed');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await authAPI.login({ email: formData.email, password: formData.password });
      if (res.data.requires_2fa) {
        setPendingUserId(res.data.user_id);
        setMode('2fa-login');
        setOtpCode(['', '', '', '', '', '']);
      } else {
        localStorage.setItem('access_token', res.data.access_token);
        localStorage.setItem('user', JSON.stringify(res.data.user));
        onLogin(res.data.user);
        navigate('/');
      }
    } catch (err) {
      const serverMsg = err.response?.data?.error || err.response?.data?.message || err.message;
      if (err.code === 'ERR_NETWORK') {
        setError('Cannot connect to backend server. Make sure Flask is running on port 5001.');
      } else {
        setError(serverMsg || 'Login failed');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVerify2FASetup = async () => {
    const code = getOtpString();
    if (code.length !== 6) { setError('Enter all 6 digits'); return; }
    setLoading(true);
    setError('');
    try {
      await authAPI.verify2FASetup({ user_id: pendingUserId, otp_code: code });
      setMode('login');
      setFormData({ ...formData, password: '' });
      setError('');
      alert('2FA configured! You can now log in.');
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid code');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify2FALogin = async () => {
    const code = getOtpString();
    if (code.length !== 6) { setError('Enter all 6 digits'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await authAPI.verify2FALogin({ user_id: pendingUserId, otp_code: code });
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem('user', JSON.stringify(res.data.user));
      onLogin(res.data.user);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container fade-in">
        <div className="login-card">
          <h1 className="brand-title">RGB-Pose Hub</h1>
          <p className="brand-subtitle">6D Object Pose Estimation Platform</p>

          {error && <div className="alert alert-error">⚠ {error}</div>}

          {/* ── Login Form ── */}
          {mode === 'login' && (
            <form onSubmit={handleLogin}>
              <div className="form-group">
                <label className="form-label">Email or Username</label>
                <input className="form-input" type="text" name="email" placeholder="Enter email or username"
                  value={formData.email} onChange={handleChange} required />
              </div>
              <div className="form-group">
                <label className="form-label">Password</label>
                <input className="form-input" type="password" name="password" placeholder="Enter password"
                  value={formData.password} onChange={handleChange} required />
              </div>
              <button className="btn btn-primary btn-block btn-lg" type="submit" disabled={loading}>
                {loading ? <span className="spinner" /> : '🔐 Sign In'}
              </button>
              <p style={{ textAlign: 'center', marginTop: '1.25rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                Don't have an account?{' '}
                <a href="#" onClick={(e) => { e.preventDefault(); setMode('register'); setError(''); }}>Create one</a>
              </p>
            </form>
          )}

          {/* ── Register Form ── */}
          {mode === 'register' && (
            <form onSubmit={handleRegister}>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input className="form-input" type="text" name="full_name" placeholder="Your full name"
                  value={formData.full_name} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label className="form-label">Username</label>
                <input className="form-input" type="text" name="username" placeholder="Choose a username"
                  value={formData.username} onChange={handleChange} required />
              </div>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input className="form-input" type="email" name="email" placeholder="your@email.com"
                  value={formData.email} onChange={handleChange} required />
              </div>
              <div className="form-group">
                <label className="form-label">Password</label>
                <input className="form-input" type="password" name="password" placeholder="Min 8 characters"
                  value={formData.password} onChange={handleChange} required minLength={8} />
              </div>
              <button className="btn btn-primary btn-block btn-lg" type="submit" disabled={loading}>
                {loading ? <span className="spinner" /> : '🚀 Create Account'}
              </button>
              <p style={{ textAlign: 'center', marginTop: '1.25rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                Already have an account?{' '}
                <a href="#" onClick={(e) => { e.preventDefault(); setMode('login'); setError(''); }}>Sign in</a>
              </p>
            </form>
          )}

          {/* ── 2FA Setup ── */}
          {mode === '2fa-setup' && twoFAData && (
            <div style={{ textAlign: 'center' }}>
              <h3 style={{ marginBottom: '0.75rem', fontSize: '1.1rem' }}>📱 Set Up Two-Factor Authentication</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
                Scan this QR code with Google Authenticator, Authy, or any TOTP app:
              </p>
              <div style={{ display: 'inline-block', padding: '1rem', background: 'white', borderRadius: '12px', marginBottom: '1rem' }}>
                <img src={`data:image/png;base64,${twoFAData.qr_code}`} alt="2FA QR Code" style={{ width: '180px', height: '180px' }} />
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '1rem', wordBreak: 'break-all' }}>
                Manual key: <code style={{ color: 'var(--accent-blue)' }}>{twoFAData.secret}</code>
              </p>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '0.5rem' }}>Enter the 6-digit code from your app:</p>
              <div className="otp-inputs">
                {otpCode.map((digit, i) => (
                  <input key={i} id={`otp-${i}`} className="otp-input" type="text" maxLength={1}
                    value={digit} onChange={(e) => handleOtpChange(i, e.target.value)}
                    onKeyDown={(e) => handleOtpKeyDown(i, e)} autoFocus={i === 0} />
                ))}
              </div>
              <button className="btn btn-primary btn-block" onClick={handleVerify2FASetup} disabled={loading}>
                {loading ? <span className="spinner" /> : '✅ Verify & Complete Setup'}
              </button>
            </div>
          )}

          {/* ── 2FA Login Verification ── */}
          {mode === '2fa-login' && (
            <div style={{ textAlign: 'center' }}>
              <h3 style={{ marginBottom: '0.75rem', fontSize: '1.1rem' }}>🔐 Two-Factor Verification</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                Enter the 6-digit code from your authenticator app:
              </p>
              <div className="otp-inputs">
                {otpCode.map((digit, i) => (
                  <input key={i} id={`otp-${i}`} className="otp-input" type="text" maxLength={1}
                    value={digit} onChange={(e) => handleOtpChange(i, e.target.value)}
                    onKeyDown={(e) => handleOtpKeyDown(i, e)} autoFocus={i === 0} />
                ))}
              </div>
              <button className="btn btn-primary btn-block" onClick={handleVerify2FALogin} disabled={loading}>
                {loading ? <span className="spinner" /> : '🔓 Verify & Sign In'}
              </button>
              <p style={{ marginTop: '1rem' }}>
                <a href="#" onClick={(e) => { e.preventDefault(); setMode('login'); setOtpCode(['','','','','','']); setError(''); }}
                  style={{ fontSize: '0.85rem' }}>← Back to login</a>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
