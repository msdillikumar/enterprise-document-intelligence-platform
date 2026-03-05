"""
Document Detail Page – Deep-dive into a single document with
SHAP explainability, anomaly analysis, and entity inspection.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import json
from api_client import get_document, get_entities  # type: ignore[import-not-found]


def render():
    st.markdown("# 🔬 Document Detail")
    st.markdown("*Deep-dive into extraction results, SHAP analysis, and anomaly detection*")
    st.markdown("---")

    # ── Document ID Input ─────────────────────────────────────────────
    doc_id = st.number_input("Enter Document ID", min_value=1, step=1, value=1)

    if st.button("🔍 Load Document", type="primary"):
        st.session_state["detail_doc_id"] = doc_id

    if "detail_doc_id" not in st.session_state:
        st.info("Enter a document ID and click Load to view details.")
        return

    doc = get_document(st.session_state["detail_doc_id"])
    if "error" in doc:
        st.error(f"Error: {doc['error']}")
        return

    # ── Header ────────────────────────────────────────────────────────
    status = doc.get("status", "unknown")
    status_icon = {"completed": "✅", "failed": "❌", "processing": "⏳"}.get(status, "⚪")

    st.markdown(f"## {status_icon} {doc.get('filename', 'Unknown')}")

    h1, h2, h3, h4, h5 = st.columns(5)
    with h1:
        st.metric("Document ID", doc.get("id"))
    with h2:
        st.metric("File Type", doc.get("file_type", ""))
    with h3:
        size_kb = (doc.get("file_size") or 0) / 1024
        st.metric("Size", f"{size_kb:.1f} KB")
    with h4:
        st.metric("Processing", f"{doc.get('processing_time_ms', 0)}ms")
    with h5:
        st.metric("Method", doc.get("extraction_method", ""))

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "🔍 SHAP Explainability",
        "⚠️ Anomaly Detection",
        "📝 Extracted Text",
        "🏷️ Entities",
    ])

    # ── Tab 1: Overview ───────────────────────────────────────────────
    with tab1:
        ov1, ov2 = st.columns(2)

        with ov1:
            st.markdown("### Confidence Score")
            conf = doc.get("confidence_score") or 0
            conf_details = doc.get("confidence_details") or {}

            st.progress(conf, text=f"{conf:.1%} — Grade {conf_details.get('grade', 'N/A')}")

            st.markdown("**Score Breakdown:**")
            breakdown = {
                "OCR Quality": conf_details.get("ocr_quality", 0),
                "Entity Confidence": conf_details.get("entity_confidence", 0),
                "Text Completeness": conf_details.get("text_completeness", 0),
            }
            bd_df = pd.DataFrame(
                {"Factor": breakdown.keys(), "Score": breakdown.values()}
            )
            st.bar_chart(bd_df.set_index("Factor"))

        with ov2:
            st.markdown("### Compliance & Authenticity")

            comp = doc.get("compliance_status", "unknown") or "unknown"
            comp_colors = {
                "compliant": "🟢",
                "warning": "🟡",
                "non_compliant": "🔴",
            }
            st.markdown(f"**Compliance:** {comp_colors.get(comp, '⚪')} {comp.upper()}")

            auth = doc.get("is_authentic")
            auth_icon = "✅" if auth else ("❌" if auth is False else "❓")
            st.markdown(f"**Authentic:** {auth_icon} {'Yes' if auth else 'No' if auth is False else 'Unknown'}")

            # Compliance details
            comp_details = doc.get("compliance_details") or {}
            if comp_details:
                auth_data = comp_details.get("authenticity", {})
                if auth_data:
                    st.markdown(f"**Authenticity Score:** {auth_data.get('authenticity_score', 0):.1%}")
                    signals = auth_data.get("signals", [])
                    for sig in signals:
                        sig_icon = {"pass": "✅", "warning": "⚠️", "fail": "❌"}.get(sig["status"], "•")
                        st.caption(f"{sig_icon} {sig['message']}")

    # ── Tab 2: SHAP Explainability ────────────────────────────────────
    with tab2:
        st.markdown("### 🔍 SHAP Feature Attribution Analysis")
        explainability = doc.get("explainability") or {}

        if not explainability:
            st.info("No explainability data available.")
        else:
            # Summary
            st.info(explainability.get("summary", ""))

            # Global feature importance
            st.markdown("#### Global Feature Importance")
            global_imp = explainability.get("global_feature_importance", {})
            if global_imp:
                imp_df = pd.DataFrame({
                    "Feature": list(global_imp.keys()),
                    "Importance": list(global_imp.values()),
                }).sort_values("Importance", ascending=False)
                st.bar_chart(imp_df.set_index("Feature"))

            # Per-entity SHAP
            st.markdown("#### Per-Entity SHAP Values")
            entity_explanations = explainability.get("entity_explanations", [])

            for i, expl in enumerate(entity_explanations):
                meets = "✅" if expl.get("meets_threshold") else "⚠️"
                with st.expander(
                    f"{meets} {expl.get('entity_type', '')} — "
                    f"\"{expl.get('entity_value', '')}\" — "
                    f"conf: {expl.get('confidence', 0):.2f}"
                ):
                    st.markdown(f"**Reason:** {expl.get('reason', '')}")
                    st.markdown(f"**Method:** `{expl.get('method', '')}`")

                    # SHAP values chart
                    shap_vals = expl.get("shap_values", {})
                    if shap_vals:
                        sv_df = pd.DataFrame({
                            "Feature": list(shap_vals.keys()),
                            "SHAP Value": list(shap_vals.values()),
                        })
                        st.bar_chart(sv_df.set_index("Feature"))

                    # Top contributors
                    top = expl.get("top_contributors", [])
                    if top:
                        st.markdown("**Top Contributing Factors:**")
                        for tc in top:
                            arrow = "↑" if tc["direction"] == "positive" else "↓"
                            st.markdown(
                                f"- {arrow} **{tc['feature']}** "
                                f"({tc['contribution']:+.4f}): {tc['explanation']}"
                            )

            # Warnings
            warnings = explainability.get("warnings", [])
            if warnings:
                st.markdown("#### ⚠️ Warnings")
                for w in warnings:
                    st.warning(w)

    # ── Tab 3: Anomaly Detection ──────────────────────────────────────
    with tab3:
        st.markdown("### ⚠️ Anomaly Detection Report")
        anomaly = doc.get("anomaly_details") or {}

        if not anomaly:
            st.info("No anomaly data available.")
        else:
            # Score
            score = anomaly.get("anomaly_score", 0)
            verdict = anomaly.get("verdict", "UNKNOWN")
            verdict_colors = {
                "NORMAL": "green",
                "SLIGHTLY_UNUSUAL": "orange",
                "ANOMALOUS": "red",
                "HIGHLY_ANOMALOUS": "red",
            }

            a1, a2, a3 = st.columns(3)
            with a1:
                st.metric("Anomaly Score", f"{score:.4f}")
            with a2:
                st.metric("Verdict", verdict)
            with a3:
                st.metric("Anomaly Flags", anomaly.get("flag_count", 0))

            st.progress(min(score, 1.0), text=f"Anomaly Score: {score:.4f}")

            # Flags
            flags = anomaly.get("flags", [])
            if flags:
                st.markdown("#### 🚩 Anomaly Flags")
                for flag in flags:
                    severity_icon = {
                        "high": "🔴",
                        "medium": "🟠",
                        "low": "🟡",
                    }.get(flag["severity"], "⚪")
                    st.markdown(
                        f"{severity_icon} **{flag['rule']}** ({flag['severity']}): "
                        f"{flag['message']}"
                    )
                    st.caption(f"💡 {flag.get('recommendation', '')}")

            # Z-scores
            z_scores = anomaly.get("z_scores", {})
            if z_scores:
                st.markdown("#### 📊 Feature Z-Scores")
                z_df = pd.DataFrame({
                    "Feature": list(z_scores.keys()),
                    "Z-Score": list(z_scores.values()),
                }).sort_values("Z-Score", key=abs, ascending=False)
                st.bar_chart(z_df.set_index("Feature"))

            # Outlier features
            outliers = anomaly.get("outlier_features", [])
            if outliers:
                st.markdown("#### 🔍 Outlier Features (|z| > 1.5)")
                for o in outliers:
                    st.markdown(
                        f"- **{o['feature']}**: z={o['z_score']:.2f}, "
                        f"actual={o['actual']}"
                    )

    # ── Tab 4: Extracted Text ─────────────────────────────────────────
    with tab4:
        t1, t2 = st.columns(2)

        with t1:
            st.markdown("### 📝 Raw OCR Text")
            raw = doc.get("raw_text", "")
            st.text_area("Raw Text", raw or "(empty)", height=400, disabled=True)

        with t2:
            st.markdown("### 🛡️ Redacted Text")
            redacted = doc.get("redacted_text", "")
            st.text_area("Redacted Text", redacted or "(empty)", height=400, disabled=True)

    # ── Tab 5: Entities ───────────────────────────────────────────────
    with tab5:
        st.markdown("### 🏷️ Extracted Entities")
        entities = doc.get("entities", [])

        if not entities:
            st.info("No entities extracted.")
        else:
            # Summary
            ent_types = {}
            for e in entities:
                t = e.get("entity_type", "unknown")
                ent_types[t] = ent_types.get(t, 0) + 1

            st.markdown(f"**{len(entities)} entities** across **{len(ent_types)} types**")

            # Type distribution chart
            type_df = pd.DataFrame({
                "Type": list(ent_types.keys()),
                "Count": list(ent_types.values()),
            }).sort_values("Count", ascending=False)
            st.bar_chart(type_df.set_index("Type"))

            # Entity table
            ent_data = []
            for e in entities:
                ent_data.append({
                    "Type": e.get("entity_type", ""),
                    "Value": e.get("entity_value", ""),
                    "Confidence": f"{e.get('confidence', 0):.2f}",
                    "PII": "🔒" if e.get("is_pii") else "",
                    "Method": e.get("extraction_method", ""),
                    "Redacted": e.get("redacted_value", ""),
                })

            ent_df = pd.DataFrame(ent_data)
            st.dataframe(ent_df, use_container_width=True, hide_index=True)
