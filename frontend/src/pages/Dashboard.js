import React, { useState, useEffect } from 'react';
import { getDocuments, getStats, deleteDocument } from '../api';
import {
  BarChart, Bar, PieChart, Pie, Cell, LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';

const COLORS = ['#3fb950', '#d29922', '#f85149', '#58a6ff', '#a371f7', '#f0883e', '#79c0ff', '#7ee787'];
const PIE_COLORS = ['#3fb950', '#d29922', '#f85149'];
const DOC_TYPE_COLORS = { invoice: '#58a6ff', purchase_order: '#a371f7', contract: '#f0883e', receipt: '#3fb950', report: '#d29922', unknown: '#8b949e' };

function Dashboard({ onViewDoc, role }) {
  const [stats, setStats] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [complianceFilter, setComplianceFilter] = useState('');
  const [docTypeFilter, setDocTypeFilter] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchData = async (searchQuery = '', status = '', compliance = '', docType = '') => {
    setLoading(true);
    try {
      const params = { limit: 50 };
      if (searchQuery) params.search = searchQuery;
      if (status) params.status = status;
      if (compliance) params.compliance = compliance;
      if (docType) params.doc_type = docType;

      const [statsRes, docsRes] = await Promise.all([
        getStats(),
        getDocuments(params),
      ]);
      setStats(statsRes.data);
      setDocuments(docsRes.data.documents);
    } catch (err) {
      console.error('Failed to fetch data:', err);
    }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchData(search, statusFilter, complianceFilter, docTypeFilter);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this document?')) return;
    try {
      await deleteDocument(id);
      fetchData(search, statusFilter, complianceFilter, docTypeFilter);
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const confBar = (score) => {
    const pct = ((score || 0) * 100).toFixed(1);
    const cls = score >= 0.75 ? 'high' : score >= 0.5 ? 'medium' : 'low';
    return (
      <div className="mini-conf">
        <div className="confidence-bar small">
          <div className={`confidence-fill ${cls}`} style={{ width: `${pct}%` }} />
        </div>
        <span className={`conf-label ${cls}`}>{pct}%</span>
      </div>
    );
  };

  if (loading) return <div className="spinner" />;

  const charts = stats?.charts || {};

  return (
    <div>
      <div className="dashboard-header">
        <h2 className="section-title">📊 Dashboard Overview</h2>
        <div className="header-badge">
          {role === 'admin' && <span className="role-badge admin">Admin View</span>}
          {role === 'auditor' && <span className="role-badge auditor">Auditor View</span>}
          {role === 'finance_user' && <span className="role-badge finance">Finance View</span>}
          {role === 'compliance_officer' && <span className="role-badge compliance">Compliance View</span>}
          {role === 'user' && <span className="role-badge user">User View</span>}
        </div>
      </div>

      {/* ── Advanced Analytics Cards ── */}
      {stats && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">📄</div>
              <div className="stat-value">{stats.total_documents}</div>
              <div className="stat-label">Total Documents</div>
            </div>
            <div className="stat-card success">
              <div className="stat-icon">✅</div>
              <div className="stat-value">{stats.completed}</div>
              <div className="stat-label">Processed</div>
            </div>
            <div className="stat-card danger">
              <div className="stat-icon">❌</div>
              <div className="stat-value">{stats.failed}</div>
              <div className="stat-label">Failed</div>
            </div>
            <div className="stat-card info">
              <div className="stat-icon">🎯</div>
              <div className="stat-value">{(stats.avg_confidence * 100).toFixed(1)}%</div>
              <div className="stat-label">Avg Confidence</div>
            </div>
            <div className="stat-card success">
              <div className="stat-icon">🛡️</div>
              <div className="stat-value">{stats.compliance_percentage}%</div>
              <div className="stat-label">Compliance Rate</div>
            </div>
            <div className="stat-card warning">
              <div className="stat-icon">⚠️</div>
              <div className="stat-value">{stats.risk_score}</div>
              <div className="stat-label">Risk Score</div>
            </div>
            <div className="stat-card info">
              <div className="stat-icon">💰</div>
              <div className="stat-value">₹{(stats.total_amount || 0).toLocaleString()}</div>
              <div className="stat-label">Total Amount</div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">🏛️</div>
              <div className="stat-value">₹{(stats.total_gst || 0).toLocaleString()}</div>
              <div className="stat-label">Total GST</div>
            </div>
          </div>

          {/* Secondary Stats */}
          <div className="stats-grid secondary">
            <div className="stat-card compact">
              <div className="stat-icon">🧠</div>
              <div className="stat-value">{stats.total_entities_extracted}</div>
              <div className="stat-label">Entities</div>
            </div>
            <div className="stat-card compact">
              <div className="stat-icon">🔴</div>
              <div className="stat-value">{stats.pii_detected}</div>
              <div className="stat-label">PII Redacted</div>
            </div>
            <div className="stat-card compact">
              <div className="stat-icon">⚡</div>
              <div className="stat-value">{stats.avg_processing_time_ms}ms</div>
              <div className="stat-label">Avg Processing</div>
            </div>
            <div className="stat-card compact">
              <div className="stat-icon">⚠️</div>
              <div className="stat-value">{stats.warning_documents}</div>
              <div className="stat-label">Warnings</div>
            </div>
          </div>
        </>
      )}

      {/* Charts Row */}
      {stats && (
        <div className="charts-grid">
          {/* Monthly Volume Area Chart */}
          {charts.monthly_volume?.length > 0 && (
            <div className="chart-card">
              <h3>📈 Monthly Document Volume</h3>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={charts.monthly_volume}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                  <XAxis dataKey="month" tick={{ fill: '#8b949e', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#8b949e' }} />
                  <Tooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8 }} />
                  <Area type="monotone" dataKey="count" stroke="#58a6ff" fill="#58a6ff20" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Document Type Pie Chart */}
          {charts.document_type_distribution?.length > 0 && (
            <div className="chart-card">
              <h3>📁 Document Types</h3>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={charts.document_type_distribution}
                    dataKey="count"
                    nameKey="type"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ type, count }) => count > 0 ? `${type}: ${count}` : ''}
                  >
                    {(charts.document_type_distribution || []).map((entry, i) => (
                      <Cell key={i} fill={DOC_TYPE_COLORS[entry.type] || COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8 }} />
                  <Legend wrapperStyle={{ color: '#8b949e' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Entity Distribution Bar Chart */}
          <div className="chart-card">
            <h3>🧠 Entity Type Distribution</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={charts.entity_distribution || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                <XAxis dataKey="type" tick={{ fill: '#8b949e', fontSize: 11 }} angle={-30} textAnchor="end" height={60} />
                <YAxis tick={{ fill: '#8b949e' }} />
                <Tooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8 }} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {(charts.entity_distribution || []).map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Compliance Pie Chart */}
          <div className="chart-card">
            <h3>🛡️ Compliance Breakdown</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={charts.compliance_breakdown || []}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, value }) => value > 0 ? `${name}: ${value}` : ''}
                >
                  {(charts.compliance_breakdown || []).map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8 }} />
                <Legend wrapperStyle={{ color: '#8b949e' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Confidence Distribution */}
          <div className="chart-card">
            <h3>📊 Confidence Distribution</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={charts.confidence_distribution || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                <XAxis dataKey="range" tick={{ fill: '#8b949e' }} />
                <YAxis tick={{ fill: '#8b949e' }} />
                <Tooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8 }} />
                <Bar dataKey="count" fill="#58a6ff" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Processing Time Line Chart */}
          <div className="chart-card">
            <h3>⚡ Recent Processing Times</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={charts.recent_processing_times || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                <XAxis dataKey="name" tick={{ fill: '#8b949e', fontSize: 11 }} />
                <YAxis tick={{ fill: '#8b949e' }} />
                <Tooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8 }} formatter={(v) => [`${v}ms`, 'Time']} />
                <Line type="monotone" dataKey="time_ms" stroke="#a371f7" strokeWidth={2} dot={{ fill: '#a371f7' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Documents Section */}
      <h2 className="section-title">📁 Documents</h2>

      {/* Enhanced Search & Filters */}
      <form className="search-bar enhanced" onSubmit={handleSearch}>
        <input
          type="text"
          placeholder="Search documents by name or content..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="filter-select">
          <option value="">All Status</option>
          <option value="completed">Completed</option>
          <option value="processing">Processing</option>
          <option value="failed">Failed</option>
        </select>
        <select value={complianceFilter} onChange={(e) => setComplianceFilter(e.target.value)} className="filter-select">
          <option value="">All Compliance</option>
          <option value="compliant">Compliant</option>
          <option value="warning">Warning</option>
          <option value="non_compliant">Non-Compliant</option>
        </select>
        <select value={docTypeFilter} onChange={(e) => setDocTypeFilter(e.target.value)} className="filter-select">
          <option value="">All Types</option>
          <option value="invoice">Invoice</option>
          <option value="purchase_order">Purchase Order</option>
          <option value="contract">Contract</option>
          <option value="receipt">Receipt</option>
          <option value="report">Report</option>
        </select>
        <button type="submit">🔍 Search</button>
      </form>

      {documents.length === 0 ? (
        <div className="empty-state">
          <div className="icon">📭</div>
          <p>No documents yet. Upload one to get started!</p>
        </div>
      ) : (
        <table className="doc-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Filename</th>
              <th>Type</th>
              <th>Status</th>
              <th>Confidence</th>
              <th>Compliance</th>
              <th>Entities</th>
              <th>Time</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id}>
                <td className="doc-id">#{doc.id}</td>
                <td className="doc-filename">{doc.filename}</td>
                <td>
                  {doc.document_type ? (
                    <span className={`badge doc-type-${doc.document_type}`} style={{ background: (DOC_TYPE_COLORS[doc.document_type] || '#8b949e') + '25', color: DOC_TYPE_COLORS[doc.document_type] || '#8b949e' }}>
                      {doc.document_type}
                    </span>
                  ) : '—'}
                </td>
                <td><span className={`badge ${doc.status}`}>{doc.status}</span></td>
                <td>{doc.confidence_score != null ? confBar(doc.confidence_score) : '—'}</td>
                <td>
                  <span className={`badge ${doc.compliance_status || ''}`}>
                    {doc.compliance_status === 'compliant' ? '✅' : doc.compliance_status === 'warning' ? '⚠️' : doc.compliance_status === 'non_compliant' ? '❌' : ''}{' '}
                    {doc.compliance_status || '—'}
                  </span>
                </td>
                <td><span className="entity-count">{doc.entities?.length || 0}</span></td>
                <td>{doc.processing_time_ms ? `${doc.processing_time_ms}ms` : '—'}</td>
                <td className="action-cell">
                  <button className="view-btn" onClick={() => onViewDoc(doc.id)}>View</button>
                  {role === 'admin' && (
                    <button className="delete-btn" onClick={() => handleDelete(doc.id)}>🗑️</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default Dashboard;
