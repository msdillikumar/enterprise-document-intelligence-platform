"""
Upload Page – Document upload with real-time processing feedback.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from api_client import upload_document  # type: ignore[import-not-found]


def render():
    st.markdown("# 📤 Upload Documents")
    st.markdown("*Upload invoices, receipts, contracts, or any business document for AI-powered analysis*")
    st.markdown("---")

    # ── Upload Area ───────────────────────────────────────────────────
    col_upload, col_info = st.columns([2, 1])

    with col_upload:
        uploaded_files = st.file_uploader(
            "Choose files to process",
            type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"],
            accept_multiple_files=True,
            help="Supported: PDF, PNG, JPG, JPEG, TIFF, BMP",
        )

        if uploaded_files:
            st.markdown(f"**{len(uploaded_files)} file(s) selected**")
            for f in uploaded_files:
                size_kb = len(f.getvalue()) / 1024
                st.markdown(f"- 📄 `{f.name}` ({size_kb:.1f} KB)")

    with col_info:
        st.markdown("### Processing Pipeline")
        st.markdown("""
        Each document goes through:

        1. 🔐 **AES-256 Encryption**
        2. 👁️ **Tesseract OCR**
        3. 🤖 **LLM Entity Extraction**
        4. 📊 **Confidence Scoring**
        5. 🔍 **SHAP Explainability**
        6. ⚠️ **Anomaly Detection**
        7. ✅ **Compliance Check**
        8. 🛡️ **PII Redaction**
        """)

    st.markdown("---")

    # ── Process Button ────────────────────────────────────────────────
    if uploaded_files:
        if st.button("🚀 Process Documents", type="primary", use_container_width=True):
            results = []
            progress = st.progress(0.0, text="Starting pipeline...")

            for i, uploaded_file in enumerate(uploaded_files):
                progress.progress(
                    (i) / len(uploaded_files),
                    text=f"Processing {uploaded_file.name}..."
                )

                file_bytes = uploaded_file.getvalue()
                result = upload_document(file_bytes, uploaded_file.name)
                results.append(result)

            progress.progress(1.0, text="Complete!")

            # ── Results ──────────────────────────────────────────────
            st.markdown("### 📋 Processing Results")

            for result in results:
                if result.get("success"):
                    pr = result.get("pipeline_results", {})
                    with st.expander(
                        f"✅ {result.get('filename', 'Unknown')} — "
                        f"Processed in {result.get('processing_time_ms', 0)}ms",
                        expanded=True,
                    ):
                        # Result metrics
                        r1, r2, r3, r4 = st.columns(4)
                        with r1:
                            ocr_conf = pr.get("ocr", {}).get("confidence", 0)
                            st.metric("OCR Confidence", f"{ocr_conf:.1f}%")
                        with r2:
                            ext = pr.get("entity_extraction", {})
                            st.metric("Entities", ext.get("entities_extracted", 0))
                        with r3:
                            conf = pr.get("confidence", {})
                            st.metric("Confidence", f"{conf.get('overall_score', 0):.1%}")
                        with r4:
                            st.metric("PII Redacted", pr.get("pii_redacted", 0))

                        # Pipeline details
                        det1, det2 = st.columns(2)
                        with det1:
                            st.markdown("**Extraction Method:**")
                            method = pr.get("entity_extraction", {}).get("method", "unknown")
                            method_labels = {
                                "llm_local": "🤖 Local LLM (Transformer)",
                                "huggingface_ner": "🌐 HuggingFace NER",
                                "regex_pattern": "🔤 Pattern Matching",
                            }
                            st.info(method_labels.get(method, method))

                        with det2:
                            st.markdown("**Anomaly Detection:**")
                            anomaly = pr.get("anomaly_detection", {})
                            verdict = anomaly.get("verdict", "NORMAL")
                            v_colors = {
                                "NORMAL": "🟢",
                                "SLIGHTLY_UNUSUAL": "🟡",
                                "ANOMALOUS": "🟠",
                                "HIGHLY_ANOMALOUS": "🔴",
                            }
                            st.info(f"{v_colors.get(verdict, '⚪')} {verdict}")

                        # SHAP summary
                        xai = pr.get("explainability", {})
                        if xai.get("summary"):
                            st.markdown("**Explainability:**")
                            st.caption(xai["summary"])

                        st.success(
                            f"Document ID: **{result.get('document_id')}** — "
                            f"View in Document Detail page"
                        )
                else:
                    st.error(
                        f"❌ {result.get('filename', 'Unknown')}: "
                        f"{result.get('error', 'Unknown error')}"
                    )
    else:
        st.markdown("""
        <div style="text-align:center; padding:60px; background:#f8f9fa;
                    border-radius:16px; border:2px dashed #d1d5db;">
            <div style="font-size:3rem;">📄</div>
            <h3 style="color:#6b7280;">Drop files here or click Browse</h3>
            <p style="color:#9ca3af;">
                Supported: PDF, PNG, JPG, JPEG, TIFF, BMP<br>
                Max recommended: 10MB per file
            </p>
        </div>
        """, unsafe_allow_html=True)
