import axios from 'axios';

const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
});

// ── Auth Token Interceptor ──────────────────────────────────────────
API.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

API.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
    return Promise.reject(err);
  }
);

// ── Auth Endpoints ──────────────────────────────────────────────────
export const login = (username, password) => {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  return API.post('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
};

export const register = (data) =>
  API.post('/auth/register', data);

export const getMe = () =>
  API.get('/auth/me');

export const getUsers = () =>
  API.get('/auth/users');

export const getRoles = () =>
  API.get('/auth/roles');

// ── Document Endpoints ──────────────────────────────────────────────
export const uploadDocument = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return API.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const getDocuments = (params = {}) =>
  API.get('/documents', { params });

export const getDocument = (id) =>
  API.get(`/documents/${id}`);

export const getStats = () =>
  API.get('/documents/stats');

export const deleteDocument = (id) =>
  API.delete(`/documents/${id}`);

export const getEntities = (id) =>
  API.get(`/documents/${id}/entities`);

// ── Export Endpoints ────────────────────────────────────────────────
export const exportJSON = (id) =>
  API.get(`/documents/${id}/export/json`, { responseType: 'blob' });

export const exportCSV = (id) =>
  API.get(`/documents/${id}/export/csv`, { responseType: 'blob' });

// ── Progress Tracking ───────────────────────────────────────────────
export const getDocumentProgress = (docId) =>
  API.get(`/documents/${docId}/progress`);

export const getActiveTasks = () =>
  API.get('/tasks/active');

// ── Audit Logs ──────────────────────────────────────────────────────
export const getAuditLogs = (params = {}) =>
  API.get('/audit-logs', { params });

export const getAuditStats = () =>
  API.get('/audit-logs/stats');

// ── Helpers ─────────────────────────────────────────────────────────
export const downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
};

export default API;
