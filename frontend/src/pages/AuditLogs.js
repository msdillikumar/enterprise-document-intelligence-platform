import React, { useState, useEffect } from 'react';
import { getAuditLogs, getAuditStats } from '../api';

function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ action: '', username: '', resource_type: '' });
  const [page, setPage] = useState(0);
  const limit = 25;

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = { skip: page * limit, limit };
      if (filters.action) params.action = filters.action;
      if (filters.username) params.username = filters.username;
      if (filters.resource_type) params.resource_type = filters.resource_type;

      const [logsRes, statsRes] = await Promise.all([
        getAuditLogs(params),
        page === 0 ? getAuditStats() : Promise.resolve(null),
      ]);
      setLogs(logsRes.data.logs || []);
      if (statsRes) setStats(statsRes.data);
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
    }
    setLoading(false);
  };

  useEffect(() => { fetchLogs(); }, [page]); // eslint-disable-line

  const handleFilter = (e) => {
    e.preventDefault();
    setPage(0);
    fetchLogs();
  };

  const actionIcon = (action) => {
    const icons = {
      login: '🔐', logout: '🚪', register: '📝', upload: '📤',
      view: '👁️', search: '🔍', download: '📥', delete: '🗑️',
      export: '📊', update: '✏️',
    };
    return icons[action] || '📋';
  };

  if (loading && logs.length === 0) return <div className="spinner" />;

  return (
    <div>
      <h2 className="section-title">📋 Audit Logs</h2>

      {/* Stats Cards */}
      {stats && (
        <div className="stats-grid small">
          <div className="stat-card">
            <div className="stat-icon">📋</div>
            <div className="stat-value">{stats.total_logs}</div>
            <div className="stat-label">Total Events</div>
          </div>
          {stats.actions_breakdown?.slice(0, 4).map((a, i) => (
            <div key={i} className="stat-card">
              <div className="stat-icon">{actionIcon(a.action)}</div>
              <div className="stat-value">{a.count}</div>
              <div className="stat-label">{a.action}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <form className="search-bar enhanced" onSubmit={handleFilter}>
        <select value={filters.action} onChange={(e) => setFilters({ ...filters, action: e.target.value })} className="filter-select">
          <option value="">All Actions</option>
          {['login', 'register', 'upload', 'view', 'search', 'delete', 'export'].map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Filter by username..."
          value={filters.username}
          onChange={(e) => setFilters({ ...filters, username: e.target.value })}
        />
        <select value={filters.resource_type} onChange={(e) => setFilters({ ...filters, resource_type: e.target.value })} className="filter-select">
          <option value="">All Resources</option>
          <option value="document">Document</option>
          <option value="auth">Auth</option>
        </select>
        <button type="submit">🔍 Filter</button>
      </form>

      {/* Logs Table */}
      {logs.length === 0 ? (
        <div className="empty-state">
          <div className="icon">📭</div>
          <p>No audit logs found</p>
        </div>
      ) : (
        <table className="doc-table audit-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Action</th>
              <th>User</th>
              <th>Resource</th>
              <th>Details</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td className="text-muted">{new Date(log.timestamp).toLocaleString()}</td>
                <td>
                  <span className={`badge action-${log.action}`}>
                    {actionIcon(log.action)} {log.action}
                  </span>
                </td>
                <td>{log.username || '—'}</td>
                <td>
                  {log.resource_type && (
                    <span className="resource-ref">
                      {log.resource_type}
                      {log.resource_id ? ` #${log.resource_id}` : ''}
                    </span>
                  )}
                </td>
                <td className="text-muted details-cell">
                  {log.details ? (
                    <span title={JSON.stringify(log.details)}>
                      {Object.entries(log.details).map(([k, v]) => `${k}: ${v}`).join(', ').slice(0, 60)}
                    </span>
                  ) : '—'}
                </td>
                <td className="text-muted">{log.ip_address || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Pagination */}
      <div className="pagination">
        <button disabled={page === 0} onClick={() => setPage(page - 1)}>← Previous</button>
        <span className="page-info">Page {page + 1}</span>
        <button disabled={logs.length < limit} onClick={() => setPage(page + 1)}>Next →</button>
      </div>
    </div>
  );
}

export default AuditLogs;
