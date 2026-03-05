"""
Documents Page – Browse, search, and filter all processed documents.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from api_client import list_documents, delete_document  # type: ignore[import-not-found]


def render():
    st.markdown("# 📄 Processed Documents")
    st.markdown("*Browse, search, and manage all processed documents*")
    st.markdown("---")

    # ── Filters ───────────────────────────────────────────────────────
    f1, f2, f3 = st.columns([2, 1, 1])
    with f1:
        search = st.text_input("🔍 Search documents", placeholder="Search by filename or text...")
    with f2:
        status_filter = st.selectbox("Status", ["All", "completed", "failed", "processing"])
    with f3:
        page_size = st.selectbox("Per page", [10, 20, 50], index=1)

    # Pagination
    if "doc_page" not in st.session_state:
        st.session_state.doc_page = 0

    skip = st.session_state.doc_page * page_size
    params = {"skip": skip, "limit": page_size}
    if status_filter != "All":
        params["status"] = status_filter
    if search:
        params["search"] = search

    # ── Fetch ─────────────────────────────────────────────────────────
    resp = list_documents(**params)
    docs = resp.get("documents", [])
    total = resp.get("total", 0)

    if "error" in resp and not docs:
        st.error(f"API Error: {resp['error']}")
        return

    st.markdown(f"**{total} documents** found")

    if not docs:
        st.info("No documents match your filters.")
        return

    # ── Table View ────────────────────────────────────────────────────
    table_data = []
    for doc in docs:
        entities = doc.get("entities", [])
        table_data.append({
            "ID": doc.get("id"),
            "Filename": doc.get("filename", ""),
            "Type": doc.get("file_type", ""),
            "Status": doc.get("status", ""),
            "Confidence": f"{(doc.get('confidence_score') or 0):.1%}",
            "Entities": len(entities),
            "Compliance": doc.get("compliance_status", ""),
            "Anomaly": f"{(doc.get('anomaly_score') or 0):.2f}",
            "Method": doc.get("extraction_method", ""),
            "Time (ms)": doc.get("processing_time_ms", 0),
            "Uploaded": (doc.get("upload_time", "") or "")[:19],
        })

    df = pd.DataFrame(table_data)

    # Color-code status
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Confidence": st.column_config.TextColumn("Confidence"),
            "Anomaly": st.column_config.TextColumn("Anomaly"),
        },
    )

    # ── Pagination Controls ───────────────────────────────────────────
    total_pages = max(1, (total + page_size - 1) // page_size)
    p1, p2, p3 = st.columns([1, 2, 1])
    with p1:
        if st.button("← Previous", disabled=st.session_state.doc_page == 0):
            st.session_state.doc_page -= 1
            st.rerun()
    with p2:
        st.markdown(
            f"<div style='text-align:center'>Page {st.session_state.doc_page + 1} of {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with p3:
        if st.button("Next →", disabled=st.session_state.doc_page >= total_pages - 1):
            st.session_state.doc_page += 1
            st.rerun()

    # ── Expanded Details ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Document Cards")

    for doc in docs:
        entities = doc.get("entities", [])
        status = doc.get("status", "unknown")
        conf = doc.get("confidence_score") or 0
        status_icon = {"completed": "✅", "failed": "❌", "processing": "⏳"}.get(status, "⚪")

        with st.expander(
            f"{status_icon} {doc.get('filename', 'Unknown')} — "
            f"ID {doc.get('id')} — {conf:.1%} confidence"
        ):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Confidence", f"{conf:.1%}")
            with c2:
                st.metric("Entities", len(entities))
            with c3:
                comp = doc.get("compliance_status", "unknown") or "unknown"
                st.metric("Compliance", comp.upper())
            with c4:
                anomaly = doc.get("anomaly_score") or 0
                st.metric("Anomaly Score", f"{anomaly:.3f}")

            # Entity summary
            if entities:
                st.markdown("**Extracted Entities:**")
                ent_types = {}
                for e in entities:
                    t = e.get("entity_type", "")
                    ent_types[t] = ent_types.get(t, 0) + 1
                ent_summary = " • ".join(f"`{t}`: {c}" for t, c in sorted(ent_types.items()))
                st.markdown(ent_summary)

            # Delete
            if st.button(f"🗑️ Delete", key=f"del_{doc.get('id')}"):
                result = delete_document(doc["id"])
                if "error" not in result:
                    st.success(f"Document {doc['id']} deleted.")
                    st.rerun()
                else:
                    st.error(result["error"])
