import React, { useState } from 'react';
import { login, register } from '../api';

function Login({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false);
  const [form, setForm] = useState({ username: '', password: '', email: '', full_name: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegister) {
        await register({
          username: form.username,
          password: form.password,
          email: form.email || undefined,
          full_name: form.full_name || undefined,
        });
        // After registration, auto-login
        const res = await login(form.username, form.password);
        localStorage.setItem('token', res.data.access_token);
        localStorage.setItem('user', JSON.stringify(res.data.user));
        onLogin(res.data.user);
      } else {
        const res = await login(form.username, form.password);
        localStorage.setItem('token', res.data.access_token);
        localStorage.setItem('user', JSON.stringify(res.data.user));
        onLogin(res.data.user);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Authentication failed');
    }
    setLoading(false);
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <span className="login-icon">📄</span>
          <h1>DocDynamo <sup className="version-badge">v4</sup></h1>
          <p className="login-subtitle">Enterprise Document Intelligence Platform</p>
        </div>

        <div className="login-tabs">
          <button className={!isRegister ? 'active' : ''} onClick={() => setIsRegister(false)}>
            Sign In
          </button>
          <button className={isRegister ? 'active' : ''} onClick={() => setIsRegister(true)}>
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              name="username"
              value={form.username}
              onChange={handleChange}
              placeholder="Enter username"
              required
              autoFocus
            />
          </div>

          {isRegister && (
            <>
              <div className="form-group">
                <label>Email (optional)</label>
                <input
                  type="email"
                  name="email"
                  value={form.email}
                  onChange={handleChange}
                  placeholder="user@example.com"
                />
              </div>
              <div className="form-group">
                <label>Full Name (optional)</label>
                <input
                  type="text"
                  name="full_name"
                  value={form.full_name}
                  onChange={handleChange}
                  placeholder="John Doe"
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              placeholder="Enter password"
              required
              minLength={4}
            />
          </div>

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="login-submit" disabled={loading}>
            {loading ? '⏳ Please wait...' : isRegister ? '🚀 Create Account' : '🔐 Sign In'}
          </button>
        </form>

        <div className="login-footer">
          <p>🔒 Secured with JWT/OAuth2 Authentication</p>
          <p>🛡️ Role-Based Access Control (RBAC)</p>
        </div>
      </div>
    </div>
  );
}

export default Login;
