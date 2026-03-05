import React, { useState, useEffect } from 'react';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import DocumentDetail from './pages/DocumentDetail';
import AuditLogs from './pages/AuditLogs';
import { getMe } from './api';
import './App.css';

const ROLE_CONFIG = {
  admin: { icon: '👑', color: '#f0883e', permissions: ['upload', 'view', 'search', 'delete', 'export', 'audit_logs', 'manage_users'] },
  auditor: { icon: '🔍', color: '#a371f7', permissions: ['view', 'search', 'export', 'audit_logs'] },
  finance_user: { icon: '💰', color: '#3fb950', permissions: ['upload', 'view', 'search', 'export'] },
  compliance_officer: { icon: '🛡️', color: '#d29922', permissions: ['view', 'search', 'export', 'audit_logs'] },
  user: { icon: '👤', color: '#58a6ff', permissions: ['upload', 'view', 'search'] },
};

function App() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [page, setPage] = useState('dashboard');
  const [selectedDocId, setSelectedDocId] = useState(null);

  // Check for existing session on mount
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    const token = localStorage.getItem('token');
    if (savedUser && token) {
      try {
        setUser(JSON.parse(savedUser));
        // Verify token is still valid
        getMe().then((res) => {
          const userData = res.data;
          setUser(userData);
          localStorage.setItem('user', JSON.stringify(userData));
        }).catch(() => {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setUser(null);
        });
      } catch {
        setUser(null);
      }
    }
    setAuthChecked(true);
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
    setPage('dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setPage('dashboard');
  };

  const navigate = (p, docId = null) => {
    setPage(p);
    setSelectedDocId(docId);
  };

  const role = user?.role || 'user';
  const roleConfig = ROLE_CONFIG[role] || ROLE_CONFIG.user;
  const hasPermission = (perm) => roleConfig.permissions.includes(perm);

  // Show loading while checking auth
  if (!authChecked) return <div className="spinner" />;

  // Show login if not authenticated
  if (!user) return <Login onLogin={handleLogin} />;

  return (
    <div className="app">
      <nav className="navbar">
        <div className="nav-brand" onClick={() => navigate('dashboard')}>
          <span className="nav-icon">📄</span>
          <span>DocDynamo <sup className="version-badge">v4</sup></span>
        </div>
        <div className="nav-links">
          <button
            className={page === 'dashboard' ? 'active' : ''}
            onClick={() => navigate('dashboard')}
          >
            📊 Dashboard
          </button>
          {hasPermission('upload') && (
            <button
              className={page === 'upload' ? 'active' : ''}
              onClick={() => navigate('upload')}
            >
              📤 Upload
            </button>
          )}
          {hasPermission('audit_logs') && (
            <button
              className={page === 'audit' ? 'active' : ''}
              onClick={() => navigate('audit')}
            >
              📋 Audit Logs
            </button>
          )}
        </div>
        <div className="nav-right">
          <div className="user-info">
            <span className="role-icon">{roleConfig.icon}</span>
            <span className="user-name">{user.full_name || user.username}</span>
            <span className="role-badge-small" style={{ background: roleConfig.color + '30', color: roleConfig.color }}>
              {role}
            </span>
          </div>
          <button className="logout-btn" onClick={handleLogout} title="Sign Out">
            🚪
          </button>
        </div>
      </nav>

      <main className="main-content">
        {page === 'dashboard' && (
          <Dashboard onViewDoc={(id) => navigate('detail', id)} role={role} />
        )}
        {page === 'upload' && hasPermission('upload') && (
          <Upload onComplete={() => navigate('dashboard')} />
        )}
        {page === 'detail' && selectedDocId && (
          <DocumentDetail
            docId={selectedDocId}
            onBack={() => navigate('dashboard')}
            role={role}
          />
        )}
        {page === 'audit' && hasPermission('audit_logs') && (
          <AuditLogs />
        )}
      </main>

      <footer className="app-footer">
        <span>Enterprise Document Intelligence Platform v4.0</span>
        <span className="footer-separator">|</span>
        <span>PaddleOCR + LLM + SHAP + JWT/RBAC</span>
        <span className="footer-separator">|</span>
        <span style={{ color: roleConfig.color }}>{roleConfig.icon} {user.username} ({role})</span>
      </footer>
    </div>
  );
}

export default App;
