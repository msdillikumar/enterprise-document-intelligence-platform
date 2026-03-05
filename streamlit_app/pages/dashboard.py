"""
Dashboard Page – Overview metrics, charts, and pipeline status.
Professional design inspired by Google Document AI console.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from api_client import get_stats, list_documents, check_health  # type: ignore[import-not-found]


def render():
    # ── Header ────────────────────────────────────────────────────────
    col_title, col_health = st.columns([4, 1])
    with col_title:
        st.markdown("# 📊 Intelligence Dashboard")
        st.markdown("*Real-time overview of document processing pipeline*")
    with col_health:
        health = check_health()
        if health.get("status") == "healthy":
            st.success("🟢 API Online")
        else:
            st.error("🔴 API Offline")

    st.markdown("---")

    # ── Fetch Stats ───────────────────────────────────────────────────
    stats = get_stats()
    if "error" in stats:
        st.error(f"Cannot reach backend: {stats['error']}")
        st.info("Make sure the FastAPI backend is running on port 8000.")
        return

    # ── Key Metrics Row ───────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Total Documents", stats.get("total_documents", 0))
    with m2:
        st.metric("Processed", stats.get("completed", 0))
    with m3:
        score = stats.get("avg_confidence", 0)
        st.metric("Avg Confidence", f"{score:.1%}")
    with m4:
        st.metric("Entities Extracted", stats.get("total_entities_extracted", 0))
    with m5:
        st.metric("PII Detected", stats.get("pii_detected", 0))

    st.markdown("")

    # ── Second Row ────────────────────────────────────────────────────
    m6, m7, m8, m9 = st.columns(4)
    with m6:
        st.metric("Failed", stats.get("failed", 0))
    with m7:
        st.metric("Compliant", stats.get("compliant_documents", 0))
    with m8:
        avg_ms = stats.get("avg_processing_time_ms", 0)
        st.metric("Avg Processing", f"{avg_ms:.0f}ms")
    with m9:
        st.metric("Processing", stats.get("processing", 0))

    st.markdown("---")

    # ── Charts ────────────────────────────────────────────────────────
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("### 📈 Processing Status Distribution")
        status_data = pd.DataFrame({
            "Status": ["Completed", "Failed", "Processing"],
            "Count": [
                stats.get("completed", 0),
                stats.get("failed", 0),
                stats.get("processing", 0),
            ],
        })
        if status_data["Count"].sum() > 0:
            st.bar_chart(status_data.set_index("Status"))
        else:
            st.info("No documents processed yet.")

    with chart_col2:
        st.markdown("### 🛡️ Compliance Overview")
        total = stats.get("total_documents", 0)
        compliant = stats.get("compliant_documents", 0)
        non_compliant = total - compliant if total > 0 else 0
        compliance_data = pd.DataFrame({
            "Status": ["Compliant", "Non-Compliant"],
            "Count": [compliant, non_compliant],
        })
        if total > 0:
            st.bar_chart(compliance_data.set_index("Status"))
        else:
            st.info("No compliance data yet.")

    st.markdown("---")

    # ── Recent Documents ──────────────────────────────────────────────
    st.markdown("### 📄 Recent Documents")
    docs_resp = list_documents(limit=10)
    docs = docs_resp.get("documents", [])

    if not docs:
        st.info("No documents yet. Upload your first document! →")
        return

    for doc in docs:
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 1])
            with c1:
                st.markdown(f"**{doc.get('filename', 'Unknown')}**")
                st.caption(f"ID: {doc.get('id')} • {doc.get('file_type', '')} • {doc.get('upload_time', '')[:19]}")
            with c2:
                status = doc.get("status", "unknown")
                color = {"completed": "🟢", "failed": "🔴", "processing": "🟡"}.get(status, "⚪")
                st.markdown(f"{color} **{status.upper()}**")
            with c3:
                conf = doc.get("confidence_score", 0) or 0
                st.markdown(f"**{conf:.1%}** confidence")
            with c4:
                comp = doc.get("compliance_status", "unknown") or "unknown"
                badge = {"compliant": "🟢", "warning": "🟡", "non_compliant": "🔴"}.get(comp, "⚪")
                st.markdown(f"{badge} {comp}")
            with c5:
                entity_count = len(doc.get("entities", []))
                st.markdown(f"**{entity_count}** entities")
            st.markdown("---")

    # ── Pipeline Architecture ─────────────────────────────────────────
    st.markdown("### 🔄 Pipeline Architecture")
    pipeline_steps = [
        ("📤", "Upload", "User document ingestion"),
        ("🔐", "AES-256 Encryption", "Fernet symmetric encryption"),
        ("👁️", "Tesseract OCR", "Text extraction from images/PDFs"),
        ("🤖", "LLM Extraction", "Transformer-based entity extraction"),
        ("📊", "Confidence Score", "Weighted multi-factor scoring"),
        ("🔍", "SHAP Explainability", "Feature attribution analysis"),
        ("⚠️", "Anomaly Detection", "Statistical outlier identification"),
        ("✅", "Compliance Check", "Rule-based validation"),
        ("🛡️", "PII Redaction", "Sensitive data masking"),
        ("💾", "Storage", "Supabase PostgreSQL persistence"),
    ]
    cols = st.columns(5)
    for i, (icon, name, desc) in enumerate(pipeline_steps):
        with cols[i % 5]:
            st.markdown(f"""
            <div style="text-align:center; background:#f0f4ff; border-radius:12px;
                        padding:16px; margin:8px 0; border:1px solid #e0e7ff;">
                <div style="font-size:2rem;">{icon}</div>
                <div style="font-weight:600; color:#4338ca; margin:4px 0;">{name}</div>
                <div style="font-size:0.75rem; color:#6b7280;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
