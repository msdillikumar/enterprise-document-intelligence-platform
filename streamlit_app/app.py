"""
Enterprise Document Intelligence Platform – Streamlit Dashboard
Professional multi-page dashboard inspired by Google Document AI & Azure.
"""
import streamlit as st

# ── Page Config (must be first st call) ──────────────────────────────
st.set_page_config(
    page_title="Document Intelligence Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for professional look ─────────────────────────────────
st.markdown("""
<style>
    /* Global */
    .main > div { padding-top: 1rem; }
    .block-container { max-width: 1400px; }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 20px 24px;
        color: white !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    div[data-testid="stMetric"] label {
        color: rgba(255,255,255,0.85) !important;
        font-size: 0.85rem;
        font-weight: 500;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: white !important;
        font-size: 2rem;
        font-weight: 700;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color: rgba(255,255,255,0.9) !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown li,
    [data-testid="stSidebar"] label {
        color: #e0e0e0 !important;
    }

    /* Status badges */
    .status-compliant {
        background: #10b981; color: white; padding: 3px 12px;
        border-radius: 20px; font-size: 0.8rem; font-weight: 600;
    }
    .status-warning {
        background: #f59e0b; color: #1a1a2e; padding: 3px 12px;
        border-radius: 20px; font-size: 0.8rem; font-weight: 600;
    }
    .status-non_compliant {
        background: #ef4444; color: white; padding: 3px 12px;
        border-radius: 20px; font-size: 0.8rem; font-weight: 600;
    }

    /* Cards */
    .doc-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 12px;
        transition: box-shadow 0.2s;
    }
    .doc-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }

    /* Pipeline steps */
    .pipeline-step {
        display: inline-block;
        background: #f0f4ff;
        border: 1px solid #667eea;
        border-radius: 8px;
        padding: 8px 16px;
        margin: 4px;
        font-size: 0.85rem;
        color: #4338ca;
        font-weight: 500;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 Document Intelligence")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["📊 Dashboard", "📤 Upload", "📄 Documents", "🔬 Document Detail"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### Pipeline Steps")
    steps = [
        "1️⃣ AES-256 Encryption",
        "2️⃣ Tesseract OCR",
        "3️⃣ LLM Entity Extraction",
        "4️⃣ Confidence Scoring",
        "5️⃣ SHAP Explainability",
        "6️⃣ Anomaly Detection",
        "7️⃣ Compliance Check",
        "8️⃣ PII Redaction",
    ]
    for s in steps:
        st.markdown(f"- {s}")

    st.markdown("---")
    st.markdown("### Technologies")
    st.markdown("""
    - **Gen AI**: LLaMA / HuggingFace
    - **OCR**: Tesseract 5.x
    - **XAI**: SHAP
    - **Encryption**: AES-256
    - **Database**: Supabase
    - **Backend**: FastAPI
    """)

    st.markdown("---")
    st.caption("v2.0.0 • Enterprise Edition")


# ── Page Router ──────────────────────────────────────────────────────
if "📊 Dashboard" in page:
    from pages import dashboard
    dashboard.render()
elif "📤 Upload" in page:
    from pages import upload
    upload.render()
elif "📄 Documents" in page:
    from pages import documents
    documents.render()
elif "🔬 Document Detail" in page:
    from pages import detail
    detail.render()
