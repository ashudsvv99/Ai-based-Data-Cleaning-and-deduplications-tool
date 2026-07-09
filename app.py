"""
IntelliClean AI — Beautiful Streamlit Frontend
Universal AI-Powered Data Cleaning & Deduplication Platform
"""
import streamlit as st
import pandas as pd
import numpy as np
import os
import tempfile
import traceback

from backend.pipeline import PipelineOrchestrator
from backend.exporter import Exporter
from backend.state_manager import StateManager

# ─────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IntelliClean AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
#  GLOBAL CSS — Premium dark-mode glassmorphism theme
# ─────────────────────────────────────────────────────────────
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

theme_css = ""
if st.session_state.theme == 'light':
    theme_css = """
/* Light Mode Overrides */
.stApp { background: #fafafa !important; color: #0f172a !important; }
.hero { background: linear-gradient(135deg, #f5f5f5 0%, #ffffff 50%, #fafafa 100%) !important; border-color: rgba(139, 92, 246, 0.2) !important; }
.hero h1 { background: linear-gradient(135deg, #3b82f6 30%, #8b5cf6 100%) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; }
.hero p { color: #475569 !important; }
.metric-card, .glass-panel, .gpanel, .db-card, .chat-container, .upload-zone, .log-box, .live-phase-track, .rule-card { background: #ffffff !important; border-color: #e2e8f0 !important; color: #1e293b !important; box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important; }
.metric-value, .db-name { color: #0f172a !important; }
.metric-sub, .metric-label, .db-desc { color: #64748b !important; }
.sec-hdr, .section-header, h1, h2, h3, h4, h5 { color: #0f172a !important; border-color: #e2e8f0 !important; }
.chat-bubble-user { background: #f3e8ff !important; border-color: #d8b4fe !important; color: #581c87 !important; }
.chat-bubble-ai { background: #fafafa !important; border-color: #e2e8f0 !important; color: #0f172a !important; }
.step-dot.wait, .lp-dot.lp-wait { background: #f5f5f5 !important; border-color: #cbd5e1 !important; color: #64748b !important; }
.step-line { background: #e2e8f0 !important; }
.step-label.wait, .lp-label.lp-wait { color: #64748b !important; }
.log-box { font-family: 'Courier New', monospace; color: #334155 !important; }
.stTabs [data-baseweb="tab-list"] { background: #e2e8f0 !important; border: 1px solid #cbd5e1 !important; }
.stTabs [data-baseweb="tab"] { color: #475569 !important; }
.stTabs [data-baseweb="tab"]:hover { color: #0f172a !important; background: rgba(0,0,0,0.05) !important; }
.stTabs [aria-selected="true"] { background: #ffffff !important; color: #7c3aed !important; box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important; }
/* Override inline styles for dark mode elements via generic catch */
div[style*="color:#94a3b8"], div[style*="color: #94a3b8"] { color: #64748b !important; }
div[style*="color:#e2e8f0"], div[style*="color: #e2e8f0"] { color: #0f172a !important; }
div[style*="color:#475569"], div[style*="color: #475569"] { color: #475569 !important; }
div[style*="color:#cbd5e1"], div[style*="color: #cbd5e1"] { color: #64748b !important; }
div[style*="color:#a78bfa"], div[style*="color: #a78bfa"] { color: #7c3aed !important; }
/* Fix Native Streamlit Widgets in Light Mode */
.stButton > button { background-color: #ffffff !important; color: #0f172a !important; border: 1px solid #cbd5e1 !important; }
.stButton > button:hover { border-color: #8b5cf6 !important; color: #8b5cf6 !important; background-color: #f8fafc !important; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #7c3aed, #9333ea) !important; color: #ffffff !important; border: none !important; }
div[data-baseweb="input"] > div, div[data-baseweb="base-input"], div[data-baseweb="select"] > div { background-color: #ffffff !important; border-color: #cbd5e1 !important; }
div[data-baseweb="input"] input, div[data-baseweb="select"] div { color: #0f172a !important; background-color: transparent !important; }
input::placeholder { color: #94a3b8 !important; }
"""

st.markdown(f"<style>{theme_css}</style>", unsafe_allow_html=True)
st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Root reset ── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #0b0d17; color: #e2e8f0; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1400px; }

/* ── Hero banner ── */
.hero {
    background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 50%, #1a0533 100%);
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 20px;
    padding: 3rem 3.5rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute; top: -60px; right: -60px;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(139,92,246,0.18) 0%, transparent 70%);
    border-radius: 50%;
}
.hero::after {
    content: '';
    position: absolute; bottom: -80px; left: 20%;
    width: 250px; height: 250px;
    background: radial-gradient(circle, rgba(236,72,153,0.12) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(139,92,246,0.15);
    border: 1px solid rgba(139,92,246,0.4);
    border-radius: 30px; padding: 4px 14px;
    font-size: 0.75rem; font-weight: 600;
    color: #a78bfa; letter-spacing: 0.05em;
    margin-bottom: 1rem;
}
.hero h1 {
    font-size: 3rem; font-weight: 800; margin: 0 0 0.5rem;
    background: linear-gradient(135deg, #e2e8f0 30%, #a78bfa 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero p {
    font-size: 1.1rem; color: #94a3b8; margin: 0; max-width: 600px; line-height: 1.7;
}

/* ── Metric cards ── */
.metric-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 1rem; margin: 1.5rem 0; }
.metric-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px; padding: 1.4rem 1.6rem;
    display: flex; flex-direction: column; gap: 6px;
    transition: border-color 0.2s, transform 0.2s;
}
.metric-card:hover { border-color: rgba(139,92,246,0.5); transform: translateY(-2px); }
.metric-label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; }
.metric-value { font-size: 2rem; font-weight: 700; color: #e2e8f0; line-height: 1; }
.metric-sub { font-size: 0.8rem; color: #94a3b8; }
.metric-card.purple .metric-value { color: #a78bfa; }
.metric-card.pink   .metric-value { color: #f472b6; }
.metric-card.cyan   .metric-value { color: #22d3ee; }
.metric-card.green  .metric-value { color: #4ade80; }

/* ── Pipeline steps ── */
.steps-container { display: flex; flex-direction: column; gap: 0; }
.step-row {
    display: flex; align-items: flex-start; gap: 14px; padding: 8px 0;
}
.step-dot {
    width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.7rem; font-weight: 700;
}
.step-dot.done   { background: rgba(74,222,128,0.15); border: 2px solid #4ade80; color: #4ade80; }
.step-dot.active { background: rgba(139,92,246,0.2);  border: 2px solid #a78bfa; color: #a78bfa; animation: pulse 1.5s infinite; }
.step-dot.wait   { background: rgba(255,255,255,0.04); border: 2px solid rgba(255,255,255,0.12); color: #475569; }
@keyframes pulse { 0%,100%{box-shadow:0 0 0 0 rgba(139,92,246,0.3)} 50%{box-shadow:0 0 0 8px rgba(139,92,246,0)} }
.step-line { width: 2px; min-height: 16px; background: rgba(255,255,255,0.07); margin-left: 13px; }
.step-label { font-size: 0.82rem; font-weight: 500; color: #94a3b8; padding-top: 4px; }
.step-label.done   { color: #4ade80; }
.step-label.active { color: #a78bfa; font-weight: 600; }

/* ── Upload zone ── */
.upload-zone {
    border: 2px dashed rgba(139,92,246,0.35);
    border-radius: 16px; padding: 2.5rem 2rem; text-align: center;
    background: rgba(139,92,246,0.04);
    transition: border-color 0.2s, background 0.2s;
}
.upload-zone:hover { border-color: rgba(139,92,246,0.7); background: rgba(139,92,246,0.07); }

/* ── Section headers ── */
.section-header {
    display: flex; align-items: center; gap: 10px;
    font-size: 1rem; font-weight: 700; color: #e2e8f0;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    padding-bottom: 0.6rem; margin: 1.8rem 0 1rem;
}
.section-badge {
    background: rgba(139,92,246,0.15); border: 1px solid rgba(139,92,246,0.3);
    border-radius: 6px; padding: 2px 8px;
    font-size: 0.7rem; font-weight: 700; color: #a78bfa;
}

/* ── Glass panels ── */
.glass-panel {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 1.4rem 1.6rem; margin-bottom: 1rem;
}
.glass-panel.success { border-color: rgba(74,222,128,0.25); background: rgba(74,222,128,0.04); }
.glass-panel.warning { border-color: rgba(251,191,36,0.25); background: rgba(251,191,36,0.04); }
.glass-panel.error   { border-color: rgba(248,113,113,0.25); background: rgba(248,113,113,0.04); }

/* ── Tag chips ── */
.tag {
    display: inline-block; border-radius: 6px; padding: 2px 10px;
    font-size: 0.72rem; font-weight: 600; margin: 2px;
}
.tag-purple { background: rgba(139,92,246,0.15); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); }
.tag-cyan   { background: rgba(34,211,238,0.12);  color: #22d3ee; border: 1px solid rgba(34,211,238,0.3); }
.tag-green  { background: rgba(74,222,128,0.12);  color: #4ade80; border: 1px solid rgba(74,222,128,0.3); }
.tag-red    { background: rgba(248,113,113,0.12); color: #f87171; border: 1px solid rgba(248,113,113,0.3); }
.tag-gray   { background: rgba(100,116,139,0.15); color: #94a3b8; border: 1px solid rgba(100,116,139,0.3); }

/* ── Imputation rule card ── */
.rule-card {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
    border-left: 3px solid #a78bfa; border-radius: 10px;
    padding: 0.9rem 1.2rem; margin-bottom: 0.6rem;
    font-size: 0.85rem;
}

/* ── Log box ── */
.log-box {
    background: #060810; border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px; padding: 1rem 1.2rem;
    font-family: 'Courier New', monospace; font-size: 0.78rem;
    color: #94a3b8; max-height: 300px; overflow-y: auto;
    line-height: 1.7; white-space: pre-wrap;
}

/* ── Spinner animation ── */
@keyframes spin { to { transform: rotate(360deg); } }
.phase-spinner {
    display: inline-block;
    animation: spin 0.8s linear infinite;
    font-style: normal;
}

/* ── Live phase tracker ── */
.live-phase-track {
    display: flex;
    align-items: center;
    gap: 0;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 1rem 1.4rem;
    margin-bottom: 1rem;
    overflow-x: auto;
    flex-wrap: nowrap;
}
.lp-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    min-width: 80px;
    text-align: center;
    flex-shrink: 0;
}
.lp-dot {
    width: 32px; height: 32px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 700;
    flex-shrink: 0;
}
.lp-dot.lp-done   { background: rgba(74,222,128,0.15); border: 2px solid #4ade80; color: #4ade80; }
.lp-dot.lp-active { background: rgba(139,92,246,0.25); border: 2px solid #a78bfa; color: #a78bfa; box-shadow: 0 0 12px rgba(139,92,246,0.4); }
.lp-dot.lp-wait   { background: rgba(255,255,255,0.03); border: 2px solid rgba(255,255,255,0.1); color: #374151; }
.lp-label { font-size: 0.62rem; font-weight: 500; line-height: 1.3; max-width: 72px; }
.lp-label.lp-done   { color: #4ade80; }
.lp-label.lp-active { color: #a78bfa; font-weight: 700; }
.lp-label.lp-wait   { color: #374151; }
.lp-connector {
    width: 28px; height: 2px;
    flex-shrink: 0;
    margin-bottom: 18px;
}
.lp-connector.lp-done { background: #4ade80; }
.lp-connector.lp-active { background: linear-gradient(90deg, #4ade80, #a78bfa); }
.lp-connector.lp-wait  { background: rgba(255,255,255,0.07); }

/* ── Download button overrides ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #7c3aed, #a855f7) !important;
    color: white !important; border: none !important;
    border-radius: 10px !important; font-weight: 600 !important;
    padding: 0.6rem 1.4rem !important; width: 100% !important;
    transition: opacity 0.2s !important;
}
.stDownloadButton > button:hover { opacity: 0.88 !important; }

/* ── Primary button ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed 0%, #9333ea 100%) !important;
    border: none !important; border-radius: 12px !important;
    font-weight: 700 !important; font-size: 1rem !important;
    padding: 0.8rem 2rem !important; color: white !important;
    box-shadow: 0 4px 24px rgba(124,58,237,0.4) !important;
    transition: transform 0.15s, box-shadow 0.15s !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 32px rgba(124,58,237,0.5) !important;
}

/* ── Sidebar - Hide entirely ── */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }
button[kind="header"] { display: none !important; }
[data-testid="stSidebar"] .stMarkdown h3 { color: #a78bfa; font-size: 0.85rem; }

/* ── Tab styling ── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 12px !important; padding: 4px !important;
    border: 1px solid rgba(255,255,255,0.07) !important; gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important; padding: 8px 20px !important;
    color: #64748b !important; font-weight: 600 !important; font-size: 0.85rem !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(139,92,246,0.2) !important;
    color: #a78bfa !important;
}

/* ── DataFrame ── */
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

/* ── Progress bar ── */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #7c3aed, #ec4899) !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 10px !important; border: 1px solid rgba(255,255,255,0.07) !important;
}
</style>
""", unsafe_allow_html=True)



# ─────────────────────────────────────────────────────────────
#  THEME TOGGLE & HEADER INDICATOR
# ─────────────────────────────────────────────────────────────
lm_url = os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1")
os.environ["LM_STUDIO_URL"] = lm_url

import requests
@st.cache_data(ttl=5, show_spinner=False)
def check_llm_status(url: str) -> bool:
    try:
        res = requests.get(f"{url}/models", timeout=0.5)
        return res.status_code == 200
    except Exception:
        return False

# Build inline LLM status HTML (no fixed position)
if check_llm_status(lm_url):
    indicator_html = """
    <div style='display: flex; align-items: center; gap: 6px; font-size: 0.8rem; background: rgba(0,0,0,0.2); padding: 8px 14px; border-radius: 20px; border: 1px solid rgba(16, 185, 129, 0.3);'>
        <div style='width:8px;height:8px;border-radius:50%;background:#10b981;box-shadow:0 0 8px #10b981'></div>
        <span style='color:#10b981; font-weight: 600;'>LLM Online</span>
    </div>
    """
else:
    indicator_html = """
    <div style='display: flex; align-items: center; gap: 6px; font-size: 0.8rem; background: rgba(0,0,0,0.2); padding: 8px 14px; border-radius: 20px; border: 1px solid rgba(239, 68, 68, 0.3);'>
        <div style='width:8px;height:8px;border-radius:50%;background:#ef4444;box-shadow:0 0 8px #ef4444'></div>
        <span style='color:#ef4444; font-weight: 600;'>LLM Offline</span>
    </div>
    """

col_theme, col_config, col_spacer, col_status = st.columns([1, 1.5, 6.5, 1.5])
with col_theme:
    if st.button("☀️ Light" if st.session_state.theme == 'dark' else "🌙 Dark", use_container_width=True):
        st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'
        st.rerun()

with col_config:
    if st.button("⚙️ Global Config", use_container_width=True):
        from components.settings_modal import render_settings_modal
        render_settings_modal()

with col_status:
    st.markdown(f"<div style='display:flex; justify-content:flex-end; padding-top:2px'>{indicator_html}</div>", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  HERO HEADER
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <div class="hero-badge">✦ AI-Powered · Multilingual · Universal</div>
  <h1>IntelliClean AI</h1>
  <p>Upload any messy dataset — CSV or Excel — and our 12-phase AI pipeline will automatically detect languages, translate values, resolve entities, deduplicate records, and fill missing data using Gemma 2B as the reasoning engine.</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
#  DATA INGESTION
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📥 <span>Data Ingestion</span></div>', unsafe_allow_html=True)

ingest_method = st.radio(
    "Choose Data Source", 
    ["📄 Local File (CSV / Excel)", "🗄️ Live Database Connection"],
    horizontal=True,
    label_visibility="collapsed"
)

uploaded_file = None

if ingest_method == "📄 Local File (CSV / Excel)":
    uploaded_file = st.file_uploader(
        "Drop your CSV or Excel file here",
        type=["csv", "xlsx", "xls"],
        on_change=lambda: [st.session_state.pop("pipeline_results_ready", None), StateManager.clear_pipeline_state()]
    )

    if uploaded_file is None:
        st.markdown("""
        <div class="upload-zone">
          <div style="font-size:2.5rem;margin-bottom:0.7rem">📊</div>
          <div style="font-size:1rem;font-weight:600;color:#94a3b8;margin-bottom:0.3rem">Drag & drop your dataset here</div>
          <div style="font-size:0.8rem;color:#475569">Supports CSV, XLSX, XLS · Up to 200 MB</div>
        </div>
        """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="background:rgba(139,92,246,0.05);border:1px solid rgba(139,92,246,0.3);border-radius:12px;padding:2.5rem;text-align:center;margin-bottom:1rem;">
      <div style="font-size:3rem;margin-bottom:1rem">🗄️</div>
      <div style="font-size:1.4rem;font-weight:700;color:#e2e8f0;margin-bottom:0.5rem">Connect to a Live Database</div>
      <div style="font-size:0.9rem;color:#94a3b8;margin-bottom:1.5rem">
        Query, clean, and write back directly to PostgreSQL, MySQL, SQL Server, Oracle, and DB2.
      </div>
    """, unsafe_allow_html=True)
    
    # Render button to open modal or switch page
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("Launch Database Studio 🚀", type="primary", use_container_width=True):
            st.switch_page("pages/Live_Database.py")
            
    st.markdown("</div>", unsafe_allow_html=True)


if uploaded_file is None:
    st.markdown("""
    <div class="metric-grid" style="margin-top:1.5rem">
      <div class="metric-card purple">
        <div class="metric-label">Languages Supported</div>
        <div class="metric-value">12+</div>
        <div class="metric-sub">Hindi, Tamil, Telugu & more</div>
      </div>
      <div class="metric-card cyan">
        <div class="metric-label">Pipeline Phases</div>
        <div class="metric-value">12</div>
        <div class="metric-sub">End-to-end automation</div>
      </div>
      <div class="metric-card pink">
        <div class="metric-label">Cleaning Modules</div>
        <div class="metric-value">8</div>
        <div class="metric-sub">Specialized agents</div>
      </div>
      <div class="metric-card green">
        <div class="metric-label">LLM Chunk Size</div>
        <div class="metric-value">12</div>
        <div class="metric-sub">Items per API call</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

else:
    # ── File info banner ──
    file_size_kb = round(len(uploaded_file.getvalue()) / 1024, 1)
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()

    st.markdown(f"""
    <div class="glass-panel success" style="display:flex;align-items:center;gap:16px">
      <div style="font-size:2rem">✅</div>
      <div>
        <div style="font-weight:700;color:#4ade80;font-size:0.95rem">{uploaded_file.name}</div>
        <div style="font-size:0.78rem;color:#64748b;margin-top:2px">
          {file_size_kb} KB &nbsp;·&nbsp; {file_ext.upper()} format &nbsp;·&nbsp; Ready to process
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Preview and Stats ──
    try:
        if file_ext == ".csv":
            full_df = pd.read_csv(uploaded_file)
        else:
            full_df = pd.read_excel(uploaded_file)
        uploaded_file.seek(0)
        
        preview_df = full_df.head(5)

        with st.expander("👁 View Dataset Overview & Statistics", expanded=False):
            st.markdown(f'<span class="tag tag-gray">{full_df.shape[0]:,} rows</span> <span class="tag tag-gray">{full_df.shape[1]} columns detected</span>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            tab_prev, tab_stats, tab_info = st.tabs(["📄 Data Preview", "📈 Statistical Summary", "❓ Missing Values"])
            
            with tab_prev:
                st.dataframe(preview_df, use_container_width=True)
            
            with tab_stats:
                if not full_df.select_dtypes(include=[np.number]).empty:
                    st.dataframe(full_df.describe(), use_container_width=True)
                else:
                    st.info("No numeric columns found to generate statistical summary.")
                    
            with tab_info:
                import config
                temp_df = full_df.replace(config.MISSING_VALUE_MARKERS, pd.NA)
                temp_df = temp_df.replace(r'^\s*$', pd.NA, regex=True)
                missing_counts = temp_df.isna().sum()
                missing_df = pd.DataFrame({
                    "Column": missing_counts.index,
                    "Missing Values": missing_counts.values,
                    "Missing %": (missing_counts.values / len(full_df) * 100).round(2),
                    "Data Type": full_df.dtypes.astype(str).values
                })
                missing_df = missing_df[missing_df["Missing Values"] > 0].sort_values("Missing Values", ascending=False)
                
                if missing_counts.sum() > 0:
                    st.dataframe(missing_df, use_container_width=True)
                else:
                    st.success("No missing values found in the uploaded dataset!")
    except Exception as e:
        st.error(f"Could not load preview: {e}")
        uploaded_file.seek(0)

    # ── Save to temp file ──
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, f"uploaded_data{file_ext}")
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Run button ──
    col_run, col_spacer = st.columns([1, 2])
    with col_run:
        run_clicked = st.button("🚀  Start AI Cleaning Pipeline", type="primary", use_container_width=True)

    # State Management Logic
    if run_clicked:
        st.session_state["pipeline_results_ready"] = True
        st.session_state["run_pipeline_now"] = True
        StateManager.clear_pipeline_state()
        
    if not st.session_state.get("pipeline_results_ready"):
        df_cache, meta_cache, _, _ = StateManager.load_pipeline_state()
        if df_cache is not None and meta_cache is not None:
            st.session_state["pipeline_results_ready"] = True
            st.session_state["cached_df"] = df_cache
            st.session_state["cached_meta"] = meta_cache

    if st.session_state.get("pipeline_results_ready"):
        # ── Section header ──
        st.markdown('<div class="section-header">⚡ <span>Pipeline Execution</span></div>', unsafe_allow_html=True)

        # ── Phase names and their keywords that trigger them ──
        PHASE_DEFS = [
            ("Phase 1",  "Load & Profile",       "Phase 1"),
            ("Phase 2",  "AI Schema",            "Phase 2"),
            ("Phase 3",  "Strategy Plan",        "Phase 3"),
            ("Phase 4",  "Pre-Cleaning",         "Phase 4"),
            ("Phase 5",  "Translation",          "Phase 5"),
            ("Phase 6",  "Entity Resolution",    "Phase 6"),
            ("Phase 7",  "Domain Rules",         "Phase 7"),
            ("Phase 8",  "Deduplication",        "Phase 8"),
            ("Phase 9",  "Imputation",           "Phase 9"),
            ("Phase 10", "Outliers",             "Phase 10"),
            ("Phase 11", "Validation",           "Phase 11"),
            ("Phase 12", "Audit Trail",          "Phase 12"),
        ]
        PHASE_PROGRESS = {f"Phase {i+1}": int(((i+1)/12)*100) for i in range(12)}
        PHASE_PROGRESS["Completed"] = 100

        phase_tracker = st.empty()   # live horizontal phase tracker
        progress_bar  = st.progress(0)
        st.markdown(
            '<div style="font-size:0.78rem;font-weight:600;color:#64748b;'
            'letter-spacing:0.06em;text-transform:uppercase;margin:1rem 0 0.4rem">'
            '⚙️ Pipeline Execution Logs</div>',
            unsafe_allow_html=True
        )
        log_placeholder = st.empty()

        logs = []
        current_phase_idx = [0]   # mutable reference so closure can update it

        def _render_phase_tracker(active_idx: int, done: bool = False):
            """Render the horizontal live phase tracker strip."""
            html = '<div class="live-phase-track">'
            for i, (pid, label, _) in enumerate(PHASE_DEFS):
                if done or i < active_idx:
                    dot_cls   = "lp-done"
                    dot_inner = "✓"
                    lbl_cls   = "lp-done"
                    conn_cls  = "lp-done"
                elif i == active_idx:
                    dot_cls   = "lp-active"
                    dot_inner = '<i class="phase-spinner">⟳</i>'
                    lbl_cls   = "lp-active"
                    conn_cls  = "lp-active"
                else:
                    dot_cls   = "lp-wait"
                    dot_inner = str(i + 1)
                    lbl_cls   = "lp-wait"
                    conn_cls  = "lp-wait"

                html += (
                    f'<div class="lp-item">'
                    f'  <div class="lp-dot {dot_cls}">{dot_inner}</div>'
                    f'  <div class="lp-label {lbl_cls}">{label}</div>'
                    f'</div>'
                )
                if i < len(PHASE_DEFS) - 1:
                    html += f'<div class="lp-connector {conn_cls}"></div>'
            html += '</div>'
            phase_tracker.markdown(html, unsafe_allow_html=True)

        # Initial render — all waiting
        _render_phase_tracker(0)

        def log_callback(msg: str):
            logs.append(msg)

            # Detect which phase we're in and advance tracker
            for i, (pid, label, keyword) in enumerate(PHASE_DEFS):
                if keyword in msg and i >= current_phase_idx[0]:
                    current_phase_idx[0] = i
                    _render_phase_tracker(i)
                    pct = PHASE_PROGRESS.get(pid, int((i+1)/12*100))
                    progress_bar.progress(pct)
                    break

            # Log box — last 40 lines, coloured keywords
            display_logs = []
            for line in logs[-40:]:
                if "Error" in line or "Failed" in line:
                    display_logs.append(f'<span style="color:#f87171">{line}</span>')
                elif "Phase" in line and ":" in line:
                    display_logs.append(f'<span style="color:#a78bfa;font-weight:600">{line}</span>')
                elif "Completed" in line or "✓" in line or "Done" in line:
                    display_logs.append(f'<span style="color:#4ade80">{line}</span>')
                elif "[Pass" in line or "[Dedup" in line or "[Domain" in line:
                    display_logs.append(f'<span style="color:#22d3ee">{line}</span>')
                else:
                    display_logs.append(line)

            log_placeholder.markdown(
                '<div class="log-box">' + "<br>".join(display_logs) + '</div>',
                unsafe_allow_html=True
            )

        # ── Execute or Load ──
        try:
            if st.session_state.get("run_pipeline_now"):
                from backend.loader import UniversalLoader
                loader = UniversalLoader.from_file(temp_path)
                df_raw = loader.load_and_optimize()
                orchestrator = PipelineOrchestrator(df=df_raw, log_callback=log_callback)
                cleaned_df, metadata = orchestrator.execute()
                
                # Save state
                st.session_state["cached_df"] = cleaned_df
                st.session_state["cached_meta"] = metadata
                StateManager.save_pipeline_state(cleaned_df, metadata, "uploaded_data", logs)
                st.session_state["run_pipeline_now"] = False
                
                if 'progress_bar' in locals():
                    progress_bar.progress(100)
                    _render_phase_tracker(0, done=True)
            else:
                cleaned_df = st.session_state["cached_df"]
                metadata = st.session_state["cached_meta"]


            # ── DELEGATE UI RENDERING TO COMPONENTS ──
            from ui_components import render_cleaning_results
            render_cleaning_results(st, cleaned_df, metadata, logs)

        except (ConnectionError, __import__('requests').exceptions.ConnectionError):
            st.markdown("""
            <div class="glass-panel error">
              <div style="font-weight:700;color:#f87171;margin-bottom:6px">🔌 LM Studio Not Connected</div>
              <div style="font-size:0.83rem;color:#94a3b8">
                Could not reach the LM Studio server. Please:<br>
                1. Open LM Studio<br>
                2. Go to the <b>Local Server</b> tab<br>
                3. Click <b>Start Server</b><br>
                4. Ensure port 1234 is open
              </div>
            </div>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.markdown(f"""
            <div class="glass-panel error">
              <div style="font-weight:700;color:#f87171;margin-bottom:6px">❌ Pipeline Error</div>
              <div style="font-size:0.83rem;color:#94a3b8">{str(e)}</div>
            </div>
            """, unsafe_allow_html=True)
            with st.expander("View full traceback"):
                st.code(traceback.format_exc(), language="python")
