import axios from 'axios';

const API_BASE = 'http://localhost:5001/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Handle 401 errors
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

// ─── Auth API ──────────────────────────────
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  verify2FASetup: (data) => api.post('/auth/verify-2fa-setup', data),
  login: (data) => api.post('/auth/login', data),
  verify2FALogin: (data) => api.post('/auth/verify-2fa-login', data),
  logout: () => api.post('/auth/logout'),
  getProfile: () => api.get('/auth/profile'),
  updateProfile: (data) => api.put('/auth/profile', data),
  getHistory: (params) => api.get('/auth/history', { params }),
  getSessions: () => api.get('/auth/sessions'),
  revokeSession: (id) => api.post(`/auth/sessions/${id}/revoke`),
  getStats: () => api.get('/auth/stats'),
};

// ─── Data API ──────────────────────────────
export const dataAPI = {
  getStatus: () => api.get('/data/status'),
  downloadDataset: () => api.post('/data/download'),
  listObjects: () => api.get('/data/objects'),
  getObjectImage: (filename) => `${API_BASE}/data/objects/${filename}/image`,
  cleanDataset: (data) => api.post('/data/clean', data),
  preprocessDataset: (data) => api.post('/data/preprocess', data),
  uploadImage: (formData) => api.post('/data/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
};

// ─── ML API ────────────────────────────────
export const mlAPI = {
  getStatus: () => api.get('/ml/status'),
  buildModel: (data) => api.post('/ml/build', data),
  trainModel: (data) => api.post('/ml/train', data),
  predict: (formData) => api.post('/ml/predict', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  predictFilename: (data) => api.post('/ml/predict', data),
  predictDatasetImage: (filename) => api.post(`/ml/predict-dataset/${filename}`),
  getTrainingHistory: () => api.get('/ml/training-history'),
  forensicAnalyze: (formData) => api.post('/ml/forensic-analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  forensicAnalyzeJson: (data) => api.post('/ml/forensic-analyze', data),
  estimatePose: (data) => api.post('/ml/estimate-pose', data),
  getPointCloud3D: (data) => api.post('/ml/point-cloud-3d', data),
  getSampleRGBDImages: () => api.get('/ml/sample-rgbd-images'),
};

export default api;


