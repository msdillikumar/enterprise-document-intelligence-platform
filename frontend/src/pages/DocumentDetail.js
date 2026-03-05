import React, { useState, useEffect, useMemo } from 'react';
import { getDocument, exportJSON, exportCSV, downloadBlob } from '../api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

const ENTITY_COLORS = {
  INVOICE_NUMBER: '#58a6ff', DATE: '#a371f7', AMOUNT: '#3fb950', TOTAL_AMOUNT: '#3fb950',
  VENDOR_NAME: '#f0883e', PERSON: '#79c0ff', EMAIL: '#d29922', PHONE: '#d29922',
  SSN: '#f85149', CREDIT_CARD: '#f85149', ADDRESS: '#7ee787', TAX_ID: '#f0883e',
};

const SECTION_CONFIG = [
  { key: 'invoice', label: '📄 Invoice Information', types: ['INVOICE_NUMBER', 'DATE', 'DUE_DATE', 'PO_NUMBER'] },
  { key: 'amount', label: '💰 Financial Summary', types: ['AMOUNT', 'TOTAL_AMOUNT', 'TAX_AMOUNT', 'SUBTOTAL'] },
  { key: 'vendor', label: '🏢 Vendor / Organization', types: ['VENDOR_NAME', 'COMPANY', 'ORG', 'ADDRESS'] },
  { key: 'contact', label: '📞 Contact Information', types: ['PERSON', 'EMAIL', 'PHONE', 'EMAIL_ADDRESS', 'PHONE_NUMBER'] },
  { key: 'sensitive', label: '🔴 Sensitive / PII', types: ['SSN', 'CREDIT_CARD', 'US_SSN', 'US_PASSPORT', 'US_DRIVER_LICENSE', 'IBAN_CODE'] },
];

function DocumentDetail({ docId, onBack, role }) {
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [highlightedEntity, setHighlightedEntity] = useState(null);
  const [exporting, setExporting] = useState(null);

  useEffect(() => {
    getDocument(docId)
      .then((res) => setDoc(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [docId]);

  // Highlighted text with entity spans
  const highlightedText = useMemo(() => {
    if (!doc?.raw_text || !doc?.entities?.length) return null;
    const text = doc.raw_text;
    if (!highlightedEntity) return null;

    const entity = highlightedEntity;
    const value = entity.entity_value;
    if (!value) return null;

    const parts = [];
    let lastIdx = 0;
    let searchFrom = 0;

    while (searchFrom < text.length) {
      const idx = text.indexOf(value, searchFrom);
      if (idx === -1) break;
      if (idx > lastIdx) parts.push({ text: text.slice(lastIdx, idx), highlight: false });
      parts.push({ text: text.slice(idx, idx + value.length), highlight: true });
      lastIdx = idx + value.length;
      searchFrom = lastIdx;
    }
    if (lastIdx < text.length) parts.push({ text: text.slice(lastIdx), highlight: false });
    return parts.length > 1 ? parts : null;
  }, [doc, highlightedEntity]);

  const handleExportJSON = async () => {
    setExporting('json');
    try {
      const res = await exportJSON(docId);
      downloadBlob(res.data, `doc_${docId}_export.json`);
    } catch (e) { console.error(e); }
    setExporting(null);
  };

  const handleExportCSV = async () => {
    setExporting('csv');
    try {
      const res = await exportCSV(docId);
      downloadBlob(res.data, `doc_${docId}_entities.csv`);
    } catch (e) { console.error(e); }
    setExporting(null);
  };

  if (loading) return <div className="spinner" />;
  if (!doc) return <div className="empty-state"><p>Document not found</p></div>;

  const confidence = doc.confidence_details || {};
  const explainability = doc.explainability || {};
  const compliance = doc.compliance_details || {};
  const ocrQuality = doc.ocr_quality || {};

  const confPercent = ((doc.confidence_score || 0) * 100).toFixed(1);
  const confClass = doc.confidence_score >= 0.75 ? 'high' : doc.confidence_score >= 0.5 ? 'medium' : 'low';

  // Group entities by section
  const groupedEntities = {};
  const ungrouped = [];
  (doc.entities || []).forEach((e) => {
    const section = SECTION_CONFIG.find((s) => s.types.includes(e.entity_type));
    if (section) {
      if (!groupedEntities[section.key]) groupedEntities[section.key] = [];
      groupedEntities[section.key].push(e);
    } else {
      ungrouped.push(e);
    }
  });

  // Entity confidence chart data
  const entityChartData = (doc.entities || []).map((e) => ({
    name: `${e.entity_type}: ${(e.entity_value || '').slice(0, 15)}`,
    confidence: ((e.confidence || 0) * 100),
    type: e.entity_type,
  }));

  const tabs = [
    { key: 'overview', label: '📋 Overview' },
    { key: 'text', label: '📝 Text' },
    { key: 'entities', label: '🧠 Entities' },
    { key: 'confidence', label: '📊 Confidence' },
    { key: 'compliance', label: '🛡️ Compliance' },
  ];

  return (
    <div className="doc-detail">
      {/* Header */}
      <div className="detail-header">
        <button className="back-btn" onClick={onBack}>← Back</button>
        <div className="detail-title-group">
          <h2>{doc.filename}</h2>
          <div className="detail-meta">
            <span className={`badge ${doc.status}`}>{doc.status}</span>
            {doc.document_type && (
              <span className="badge doc-type-badge" style={{ background: '#58a6ff25', color: '#58a6ff' }}>
                📁 {doc.document_type}
              </span>
            )}
            <span className="meta-item">📁 {doc.file_type}</span>
            <span className="meta-item">📏 {(doc.file_size / 1024).toFixed(1)} KB</span>
            <span className="meta-item">⏱ {doc.processing_time_ms}ms</span>
          </div>
        </div>
        {/* Export Buttons */}
        <div className="export-buttons">
          <button className="export-btn json" onClick={handleExportJSON} disabled={exporting}>
            {exporting === 'json' ? '⏳' : '📥'} JSON
          </button>
          <button className="export-btn csv" onClick={handleExportCSV} disabled={exporting}>
            {exporting === 'csv' ? '⏳' : '📥'} CSV
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="tab-bar">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            className={`tab-btn ${activeTab === tab.key ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ═══ OVERVIEW TAB ═══ */}
      {activeTab === 'overview' && (
        <div className="detail-grid">
          {/* Document Info */}
          <div className="detail-card">
            <h3>📋 Document Info</h3>
            <div className="info-table">
              <div className="info-row"><span className="info-label">File Type</span><span>{doc.file_type}</span></div>
              <div className="info-row"><span className="info-label">File Size</span><span>{(doc.file_size / 1024).toFixed(1)} KB</span></div>
              <div className="info-row"><span className="info-label">Upload Time</span><span>{new Date(doc.upload_time).toLocaleString()}</span></div>
              <div className="info-row"><span className="info-label">Processing</span><span>{doc.processing_time_ms}ms</span></div>
              <div className="info-row"><span className="info-label">Extraction</span><span>{doc.extraction_method}</span></div>
              <div className="info-row"><span className="info-label">Status</span><span className={`badge ${doc.status}`}>{doc.status}</span></div>
            </div>
          </div>

          {/* Confidence Score - big visual */}
          <div className="detail-card">
            <h3>📊 Confidence Score</h3>
            <div className="big-score-container">
              <div className={`big-score ${confClass}`}>{confPercent}%</div>
              <div className="score-grade">Grade: {confidence.grade || 'N/A'}</div>
              <div className="confidence-bar large">
                <div className={`confidence-fill ${confClass}`} style={{ width: `${confPercent}%` }} />
              </div>
              {doc.confidence_score < 0.5 && (
                <div className="score-warning">
                  ⚠️ Low confidence — OCR quality or entity extraction may need review
                </div>
              )}
            </div>
          </div>

          {/* Compliance & Authenticity */}
          <div className="detail-card">
            <h3>🛡️ Compliance & Authenticity</h3>
            <div className="status-indicators">
              <div className="status-indicator">
                <div className="status-icon-big">{doc.is_authentic ? '✅' : '⚠️'}</div>
                <div className="status-text">{doc.is_authentic ? 'Authentic' : 'Suspicious'}</div>
              </div>
              <div className="status-indicator">
                <div className="status-icon-big">
                  {doc.compliance_status === 'compliant' ? '✅' : doc.compliance_status === 'warning' ? '⚠️' : '❌'}
                </div>
                <div className="status-text">{doc.compliance_status || 'Unknown'}</div>
              </div>
              <div className="status-indicator">
                <div className="status-icon-big">{doc.anomaly_score > 0.5 ? '🔴' : '🟢'}</div>
                <div className="status-text">
                  Anomaly: {((doc.anomaly_score || 0) * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          </div>

          {/* Extraction Summary */}
          <div className="detail-card">
            <h3>🔍 Extraction Summary</h3>
            <div className="summary-stats">
              <div className="summary-item">
                <span className="summary-number">{doc.entities?.length || 0}</span>
                <span className="summary-label">Entities</span>
              </div>
              <div className="summary-item pii">
                <span className="summary-number">{doc.entities?.filter(e => e.is_pii).length || 0}</span>
                <span className="summary-label">PII Found</span>
              </div>
              <div className="summary-item">
                <span className="summary-number">{doc.raw_text?.split(/\s+/).length || 0}</span>
                <span className="summary-label">Words</span>
              </div>
            </div>
            {explainability.summary && (
              <div className="explainability-summary">{explainability.summary}</div>
            )}
          </div>

          {/* OCR Quality */}
          {ocrQuality && ocrQuality.scan_quality_score !== undefined && (
            <div className="detail-card full-width">
              <h3>📷 OCR Quality Metrics</h3>
              <div className="quality-grid">
                <div className="quality-metric">
                  <span className="quality-metric-label">Scan Quality</span>
                  <div className="quality-bar-container">
                    <div className={`quality-bar ${ocrQuality.scan_quality_score >= 70 ? 'good' : ocrQuality.scan_quality_score >= 40 ? 'fair' : 'poor'}`}
                      style={{ width: `${ocrQuality.scan_quality_score}%` }}
                    />
                  </div>
                  <span className="quality-metric-value">{ocrQuality.scan_quality_score}%</span>
                </div>
                {ocrQuality.dpi > 0 && (
                  <div className="quality-metric">
                    <span className="quality-metric-label">DPI</span>
                    <span className={`quality-metric-value ${ocrQuality.dpi >= 300 ? 'good' : 'warning'}`}>{ocrQuality.dpi}</span>
                  </div>
                )}
                {ocrQuality.contrast && (
                  <div className="quality-metric">
                    <span className="quality-metric-label">Contrast</span>
                    <span className="quality-metric-value">{ocrQuality.contrast}</span>
                  </div>
                )}
                {ocrQuality.skew_estimate !== undefined && (
                  <div className="quality-metric">
                    <span className="quality-metric-label">Skew</span>
                    <span className={`quality-metric-value ${ocrQuality.skew_estimate > 5 ? 'warning' : 'good'}`}>
                      {ocrQuality.skew_estimate.toFixed(2)}°
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ═══ TEXT TAB ═══ with highlighting */}
      {activeTab === 'text' && (
        <div className="detail-grid">
          <div className="detail-card">
            <h3>📝 Raw Extracted Text</h3>
            {highlightedEntity && (
              <div className="highlight-indicator">
                Highlighting: <strong style={{ color: ENTITY_COLORS[highlightedEntity.entity_type] || '#58a6ff' }}>
                  {highlightedEntity.entity_type}
                </strong> = "{highlightedEntity.entity_value}"
                <button className="clear-highlight" onClick={() => setHighlightedEntity(null)}>✕</button>
              </div>
            )}
            <div className="text-preview">
              {highlightedText ? (
                highlightedText.map((part, i) => (
                  part.highlight ? (
                    <mark key={i} className="entity-highlight" style={{
                      background: (ENTITY_COLORS[highlightedEntity?.entity_type] || '#58a6ff') + '40',
                      borderBottom: `2px solid ${ENTITY_COLORS[highlightedEntity?.entity_type] || '#58a6ff'}`,
                    }}>{part.text}</mark>
                  ) : <span key={i}>{part.text}</span>
                ))
              ) : (
                doc.raw_text || 'No text extracted'
              )}
            </div>
          </div>
          <div className="detail-card">
            <h3>🛡️ Redacted Text</h3>
            <div className="text-preview">{doc.redacted_text || 'No redacted text'}</div>
          </div>
        </div>
      )}

      {/* ═══ ENTITIES TAB ═══ with visual hierarchy */}
      {activeTab === 'entities' && (
        <div>
          {/* Grouped Entity Sections */}
          {SECTION_CONFIG.map((section) => {
            const entities = groupedEntities[section.key];
            if (!entities || entities.length === 0) return null;
            return (
              <div key={section.key} className="entity-section">
                <h3 className="entity-section-title">{section.label}</h3>
                <div className="entity-cards">
                  {entities.map((e, i) => (
                    <div
                      key={i}
                      className={`entity-card ${e.is_pii ? 'pii' : ''} ${highlightedEntity === e ? 'selected' : ''}`}
                      onClick={() => {
                        setHighlightedEntity(e);
                        setActiveTab('text');
                      }}
                      style={{ borderLeftColor: ENTITY_COLORS[e.entity_type] || '#58a6ff' }}
                    >
                      <div className="entity-card-type">{e.entity_type}</div>
                      <div className="entity-card-value">
                        {e.is_pii ? e.redacted_value : e.entity_value}
                      </div>
                      <div className="entity-card-meta">
                        <span className="entity-confidence-mini">
                          {e.confidence ? `${(e.confidence * 100).toFixed(0)}%` : '—'}
                        </span>
                        {e.is_pii && <span className="pii-badge">PII</span>}
                        <span className="entity-method">{e.extraction_method}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}

          {/* Ungrouped entities */}
          {ungrouped.length > 0 && (
            <div className="entity-section">
              <h3 className="entity-section-title">📦 Other Entities</h3>
              <div className="entity-cards">
                {ungrouped.map((e, i) => (
                  <div
                    key={i}
                    className={`entity-card ${e.is_pii ? 'pii' : ''}`}
                    onClick={() => { setHighlightedEntity(e); setActiveTab('text'); }}
                  >
                    <div className="entity-card-type">{e.entity_type}</div>
                    <div className="entity-card-value">{e.is_pii ? e.redacted_value : e.entity_value}</div>
                    <div className="entity-card-meta">
                      <span>{e.confidence ? `${(e.confidence * 100).toFixed(0)}%` : '—'}</span>
                      {e.is_pii && <span className="pii-badge">PII</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(!doc.entities || doc.entities.length === 0) && (
            <div className="empty-state"><p>No entities extracted</p></div>
          )}

          {/* Entity Confidence Chart */}
          {entityChartData.length > 0 && (
            <div className="detail-card full-width" style={{ marginTop: '1.5rem' }}>
              <h3>📊 Entity Confidence Scores</h3>
              <ResponsiveContainer width="100%" height={Math.max(200, entityChartData.length * 35)}>
                <BarChart data={entityChartData} layout="vertical" margin={{ left: 120 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                  <XAxis type="number" domain={[0, 100]} tick={{ fill: '#8b949e' }} />
                  <YAxis type="category" dataKey="name" tick={{ fill: '#8b949e', fontSize: 11 }} width={120} />
                  <Tooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8 }}
                    formatter={(v) => [`${v.toFixed(1)}%`, 'Confidence']} />
                  <Bar dataKey="confidence" radius={[0, 4, 4, 0]}>
                    {entityChartData.map((entry, i) => (
                      <Cell key={i} fill={ENTITY_COLORS[entry.type] || '#58a6ff'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* ═══ CONFIDENCE TAB ═══ */}
      {activeTab === 'confidence' && (
        <div className="detail-grid">
          <div className="detail-card">
            <h3>📊 Score Breakdown</h3>
            <div className="score-breakdown">
              {[
                { label: 'OCR Quality', value: confidence.ocr_quality, icon: '📷' },
                { label: 'Entity Confidence', value: confidence.entity_confidence, icon: '🧠' },
                { label: 'Text Completeness', value: confidence.text_completeness, icon: '📝' },
              ].map((item, i) => item.value != null && (
                <div key={i} className="score-item">
                  <div className="score-item-header">
                    <span>{item.icon} {item.label}</span>
                    <span className={`score-value ${item.value >= 0.75 ? 'high' : item.value >= 0.5 ? 'medium' : 'low'}`}>
                      {(item.value * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="confidence-bar">
                    <div
                      className={`confidence-fill ${item.value >= 0.75 ? 'high' : item.value >= 0.5 ? 'medium' : 'low'}`}
                      style={{ width: `${item.value * 100}%` }}
                    />
                  </div>
                  {item.value < 0.5 && (
                    <div className="score-explanation">
                      {item.label === 'OCR Quality' && '⚠️ Low OCR quality — consider rescanning at higher DPI or better lighting'}
                      {item.label === 'Entity Confidence' && '⚠️ Entity extraction uncertain — may need manual verification'}
                      {item.label === 'Text Completeness' && '⚠️ Text appears incomplete — possible truncation or missing pages'}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
          <div className="detail-card">
            <h3>💡 Explainability</h3>
            {explainability.warnings?.length > 0 && (
              <div className="warnings-section">
                <h4>⚠️ Warnings</h4>
                {explainability.warnings.map((w, i) => (
                  <div key={i} className="warning-item">{w}</div>
                ))}
              </div>
            )}
            {explainability.entity_explanations?.slice(0, 10).map((ex, i) => (
              <div key={i} className="explanation-card">
                <div className="explanation-header">
                  <strong style={{ color: ENTITY_COLORS[ex.entity_type] || '#79c0ff' }}>{ex.entity_type}</strong>
                  <span className="explanation-value">{ex.entity_value}</span>
                </div>
                <div className="explanation-reason">{ex.reason}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ═══ COMPLIANCE TAB ═══ */}
      {activeTab === 'compliance' && (
        <div className="detail-grid">
          <div className="detail-card">
            <h3>✅ Authenticity Check</h3>
            {compliance.authenticity ? (
              <div>
                <div className="auth-verdict">
                  <div className="auth-icon">
                    {compliance.authenticity.is_authentic ? '✅' : '⚠️'}
                  </div>
                  <div className="auth-text">
                    {compliance.authenticity.is_authentic ? 'AUTHENTIC' : 'SUSPICIOUS'}
                  </div>
                  <div className="auth-score">
                    Score: {((compliance.authenticity.authenticity_score || 0) * 100).toFixed(1)}%
                  </div>
                </div>
                {compliance.authenticity.signals?.map((s, i) => (
                  <div key={i} className="signal-item">
                    <span className="signal-icon">
                      {s.status === 'pass' ? '✅' : s.status === 'warning' ? '⚠️' : '❌'}
                    </span>
                    <span className="signal-msg">{s.message}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state"><p>No authenticity data</p></div>
            )}
          </div>
          <div className="detail-card">
            <h3>📋 Compliance Check</h3>
            {compliance.compliance ? (
              <div>
                <div className="compliance-verdict">
                  <span className={`badge large ${compliance.compliance.status}`}>
                    {compliance.compliance.status?.toUpperCase()}
                  </span>
                  <div className="compliance-score">
                    {compliance.compliance.passed_checks}/{compliance.compliance.total_checks} checks passed
                  </div>
                </div>
                {compliance.compliance.issues?.map((issue, i) => (
                  <div key={i} className="signal-item">
                    <span className="signal-icon">
                      {issue.severity === 'error' ? '❌' : issue.severity === 'warning' ? '⚠️' : 'ℹ️'}
                    </span>
                    <span className="signal-msg">{issue.message}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state"><p>No compliance data</p></div>
            )}
          </div>
        </div>
      )}

      {/* Error Display */}
      {doc.error_message && (
        <div className="detail-card full-width error-card">
          <h3>❌ Processing Error</h3>
          <div className="error-message">{doc.error_message}</div>
          <div className="error-explanation">
            <strong>What this means:</strong>
            <p>The document pipeline encountered an error during processing. This could be caused by:</p>
            <ul>
              <li>Corrupted or unsupported file content</li>
              <li>OCR engine could not extract readable text</li>
              <li>Entity extraction model failed to parse the content</li>
              <li>Database connection issue during storage</li>
            </ul>
            <p><strong>Recommended:</strong> Try re-uploading the document or converting to a different format.</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default DocumentDetail;
