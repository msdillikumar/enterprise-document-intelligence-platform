import React, { useState, useRef } from 'react';
import { uploadDocument, getDocumentProgress } from '../api';

const PIPELINE_STEPS = [
  { label: 'Encrypting document (AES-256)', icon: '🔒', detail: 'Fernet symmetric encryption' },
  { label: 'Extracting text (PaddleOCR)', icon: '📝', detail: 'Layout-aware OCR with structure detection' },
  { label: 'Extracting entities (LLM / NLP)', icon: '🧠', detail: 'LLaMA 2 + HuggingFace + Regex fallback' },
  { label: 'Classifying document', icon: '📁', detail: 'Keyword + Entity hybrid classification' },
  { label: 'Computing confidence scores', icon: '📊', detail: 'Multi-factor scoring algorithm' },
  { label: 'SHAP explainability analysis', icon: '💡', detail: 'Perturbation-based feature attribution' },
  { label: 'Anomaly detection', icon: '🔍', detail: 'Statistical + GST + Duplicate checks' },
  { label: 'Compliance & authenticity check', icon: '✅', detail: 'Multi-signal validation' },
  { label: 'Redacting sensitive data (PII)', icon: '🛡️', detail: 'Presidio + pattern matching' },
  { label: 'Storing results', icon: '💾', detail: 'Database + encrypted storage' },
];

function Upload({ onComplete }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [dragover, setDragover] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState(-1);
  const [stepTimers, setStepTimers] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const inputRef = useRef();
  const startTimeRef = useRef(null);

  const handleFile = (f) => {
    setFile(f);
    setResult(null);
    setError(null);
    setCurrentStep(-1);
    setStepTimers({});

    // Generate preview for images
    if (f && f.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target.result);
      reader.readAsDataURL(f);
    } else {
      setPreview(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragover(false);
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return;
    setProcessing(true);
    setError(null);
    setResult(null);
    startTimeRef.current = Date.now();

    // Animate pipeline steps with timing
    let step = 0;
    const timers = {};
    const stepInterval = setInterval(() => {
      if (step > 0) {
        timers[step - 1] = Date.now() - startTimeRef.current;
      }
      setCurrentStep(step);
      setStepTimers({ ...timers });

      if (step >= PIPELINE_STEPS.length - 1) {
        clearInterval(stepInterval);
      }
      step++;
    }, 500);

    try {
      const res = await uploadDocument(file);
      clearInterval(stepInterval);
      // Mark all steps done
      const finalTimers = {};
      PIPELINE_STEPS.forEach((_, i) => { finalTimers[i] = res.data.processing_time_ms || 0; });
      setStepTimers(finalTimers);
      setCurrentStep(PIPELINE_STEPS.length - 1);
      setResult(res.data);
    } catch (err) {
      clearInterval(stepInterval);
      setError(err.response?.data?.detail || err.message || 'Upload failed');
    }
    setProcessing(false);
  };

  const ocrQuality = result?.pipeline_results?.ocr?.quality;

  return (
    <div>
      <h2 className="section-title">📤 Upload Document</h2>

      <div className="upload-container">
        {/* Upload Zone */}
        <div
          className={`upload-zone ${dragover ? 'dragover' : ''} ${file ? 'has-file' : ''}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
          onDragLeave={() => setDragover(false)}
          onDrop={handleDrop}
        >
          {preview ? (
            <img src={preview} alt="Preview" className="upload-preview-img" />
          ) : (
            <div className="upload-icon">📁</div>
          )}
          <div className="upload-text">
            {file ? (
              <>
                <strong>{file.name}</strong>
                <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
              </>
            ) : (
              'Click or drag & drop a document here'
            )}
          </div>
          <div className="upload-formats">
            Supported: PDF, PNG, JPG, JPEG, TIFF, BMP
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp"
            style={{ display: 'none' }}
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
        </div>

        {/* File Info Card */}
        {file && !processing && !result && (
          <div className="file-info-card">
            <div className="file-info-row">
              <span className="file-info-label">File</span>
              <span>{file.name}</span>
            </div>
            <div className="file-info-row">
              <span className="file-info-label">Size</span>
              <span>{(file.size / 1024).toFixed(1)} KB</span>
            </div>
            <div className="file-info-row">
              <span className="file-info-label">Type</span>
              <span>{file.type || 'unknown'}</span>
            </div>
            <button className="upload-btn" onClick={handleUpload}>
              🚀 Process Document
            </button>
          </div>
        )}
      </div>

      {/* Processing Pipeline Timeline */}
      {(processing || result) && (
        <div className="pipeline-timeline">
          <h3 className="pipeline-title">
            {processing ? '⏳ Processing Pipeline...' : '✅ Pipeline Complete'}
          </h3>
          <div className="timeline-track">
            {PIPELINE_STEPS.map((step, i) => {
              const isDone = result ? true : i < currentStep;
              const isActive = !result && i === currentStep;
              const isPending = !result && i > currentStep;
              return (
                <div key={i} className={`timeline-step ${isDone ? 'done' : isActive ? 'active' : 'pending'}`}>
                  <div className="timeline-marker">
                    <div className="timeline-dot">
                      {isDone ? '✅' : isActive ? <span className="pulse-dot" /> : '⬜'}
                    </div>
                    {i < PIPELINE_STEPS.length - 1 && (
                      <div className={`timeline-line ${isDone ? 'done' : ''}`} />
                    )}
                  </div>
                  <div className="timeline-content">
                    <div className="timeline-label">{step.icon} {step.label}</div>
                    <div className="timeline-detail">{step.detail}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="result-card error">
          <h3>❌ Processing Failed</h3>
          <p>{error}</p>
          <div className="error-explanation">
            <strong>Possible causes:</strong>
            <ul>
              <li>Unsupported or corrupted file format</li>
              <li>Image too small or too blurry for OCR</li>
              <li>Server processing timeout</li>
            </ul>
          </div>
        </div>
      )}

      {/* Success Result */}
      {result && (
        <div className="result-card success">
          <h3>✅ Processing Complete!</h3>

          <div className="result-grid">
            <div className="result-item">
              <span className="result-label">Document ID</span>
              <span className="result-value">#{result.document_id}</span>
            </div>
            <div className="result-item">
              <span className="result-label">Processing Time</span>
              <span className="result-value">{result.processing_time_ms}ms</span>
            </div>
            <div className="result-item">
              <span className="result-label">OCR Method</span>
              <span className="result-value">{result.pipeline_results?.ocr?.method}</span>
            </div>
            <div className="result-item">
              <span className="result-label">Entities Found</span>
              <span className="result-value">{result.pipeline_results?.entity_extraction?.entities_extracted}</span>
            </div>
            <div className="result-item">
              <span className="result-label">Confidence</span>
              <span className="result-value">
                {(result.pipeline_results?.confidence?.overall_score * 100).toFixed(1)}%
              </span>
            </div>
            <div className="result-item">
              <span className="result-label">Compliance</span>
              <span className={`badge ${result.pipeline_results?.compliance}`}>
                {result.pipeline_results?.compliance}
              </span>
            </div>
            <div className="result-item">
              <span className="result-label">Authenticity</span>
              <span className="result-value">{result.pipeline_results?.authenticity}</span>
            </div>
            <div className="result-item">
              <span className="result-label">PII Redacted</span>
              <span className="result-value">{result.pipeline_results?.pii_redacted}</span>
            </div>
          </div>

          {/* OCR Quality Indicator */}
          {ocrQuality && ocrQuality.scan_quality_score !== undefined && (
            <div className="ocr-quality-card">
              <h4>📷 Scan Quality Analysis</h4>
              <div className="quality-metrics">
                <div className="quality-item">
                  <span>Overall Quality</span>
                  <div className="quality-bar-container">
                    <div
                      className={`quality-bar ${ocrQuality.scan_quality_score >= 70 ? 'good' : ocrQuality.scan_quality_score >= 40 ? 'fair' : 'poor'}`}
                      style={{ width: `${ocrQuality.scan_quality_score}%` }}
                    />
                  </div>
                  <span className="quality-value">{ocrQuality.scan_quality_score}%</span>
                </div>
                {ocrQuality.dpi > 0 && (
                  <div className="quality-item">
                    <span>DPI</span>
                    <span className="quality-value">{ocrQuality.dpi}</span>
                  </div>
                )}
                {ocrQuality.width && (
                  <div className="quality-item">
                    <span>Resolution</span>
                    <span className="quality-value">{ocrQuality.width}×{ocrQuality.height}</span>
                  </div>
                )}
                {ocrQuality.skew_estimate !== undefined && (
                  <div className="quality-item">
                    <span>Skew</span>
                    <span className={`quality-value ${ocrQuality.skew_estimate > 5 ? 'warning' : ''}`}>
                      {ocrQuality.skew_estimate.toFixed(2)}°
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="result-actions">
            <button className="btn-primary" onClick={onComplete}>
              📊 Go to Dashboard
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Upload;
