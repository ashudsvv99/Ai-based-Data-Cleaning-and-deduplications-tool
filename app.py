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

# ─────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IntelliClean AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
#  GLOBAL CSS — Premium dark-mode glassmorphism theme
# ─────────────────────────────────────────────────────────────
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

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
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
#  SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0 0.5rem;text-align:center">
      <div style="font-size:2rem">✦</div>
      <div style="font-size:1rem;font-weight:700;color:#a78bfa">IntelliClean AI</div>
      <div style="font-size:0.72rem;color:#475569;margin-top:2px">v2.0 · Powered by Gemma 2B</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ⚙️ LLM Configuration")
    lm_url = st.text_input(
        "LM Studio Server URL",
        value="http://localhost:1234/v1",
        help="Make sure LM Studio is running with the local server enabled.",
        autocomplete="url"
    )
    os.environ["LM_STUDIO_URL"] = lm_url

    # Ping LLM to check connection for floating top-right indicator
    import requests
    
    @st.cache_data(ttl=5, show_spinner=False)
    def check_llm_status(url: str) -> bool:
        try:
            res = requests.get(f"{url}/models", timeout=0.5)
            return res.status_code == 200
        except Exception:
            return False

    if check_llm_status(lm_url):
        indicator_html = """
        <div style='position: fixed; top: 1rem; right: 1rem; z-index: 99999; display: flex; align-items: center; gap: 6px; font-size: 0.8rem; background: rgba(0,0,0,0.6); backdrop-filter: blur(10px); padding: 6px 12px; border-radius: 20px; border: 1px solid rgba(16, 185, 129, 0.2);'>
            <div style='width:8px;height:8px;border-radius:50%;background:#10b981;box-shadow:0 0 8px #10b981'></div>
            <span style='color:#10b981; font-weight: 600;'>LLM Online</span>
        </div>
        """
    else:
        indicator_html = """
        <div style='position: fixed; top: 1rem; right: 1rem; z-index: 99999; display: flex; align-items: center; gap: 6px; font-size: 0.8rem; background: rgba(0,0,0,0.6); backdrop-filter: blur(10px); padding: 6px 12px; border-radius: 20px; border: 1px solid rgba(239, 68, 68, 0.2);'>
            <div style='width:8px;height:8px;border-radius:50%;background:#ef4444;box-shadow:0 0 8px #ef4444'></div>
            <span style='color:#ef4444; font-weight: 600;'>LLM Offline</span>
        </div>
        """
        
    # Render indicator_html later in the main block so it doesn't get clipped by sidebar CSS

    st.markdown("---")
    st.markdown("### 🔄 Pipeline Phases")
    phases = [
        "Load & Profile Dataset",
        "AI Schema Classification",
        "Strategy Planning",
        "String Pre-Cleaning",
        "Multilingual Translation",
        "Entity Resolution",
        "Domain-Specific Rules",
        "Deduplication",
        "Smart Imputation",
        "Outlier Handling",
        "Validation & Scoring",
        "Audit Trail Generation",
    ]
    phase_state = st.session_state.get("phase_states", {p: "wait" for p in phases})
    html_steps = '<div class="steps-container">'
    for i, p in enumerate(phases):
        state = phase_state.get(p, "wait")
        num = str(i + 1)
        html_steps += f'<div class="step-row"><div class="step-dot {state}">{num}</div><div class="step-label {state}">{p}</div></div>'
        if i < len(phases) - 1:
            html_steps += '<div class="step-line"></div>'
    html_steps += '</div>'
    st.markdown(html_steps, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.72rem;color:#475569;line-height:1.6">
    <b style="color:#64748b">Supported formats:</b> CSV, XLSX, XLS<br>
    <b style="color:#64748b">Max file size:</b> 200 MB<br>
    <b style="color:#64748b">LLM chunk size:</b> 12 items/call<br>
    <b style="color:#64748b">Fuzzy threshold:</b> 80%
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
#  HERO HEADER
# ─────────────────────────────────────────────────────────────
st.markdown(indicator_html, unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="hero-badge">✦ AI-Powered · Multilingual · Universal</div>
  <h1>IntelliClean AI</h1>
  <p>Upload any messy dataset — CSV or Excel — and our 12-phase AI pipeline will automatically detect languages, translate values, resolve entities, deduplicate records, and fill missing data using Gemma 2B as the reasoning engine.</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
#  FILE UPLOAD
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📂 <span>Upload Dataset</span></div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Drop your CSV or Excel file here",
    type=["csv", "xlsx", "xls"]
)

if uploaded_file is None:
    st.markdown("""
    <div class="upload-zone">
      <div style="font-size:2.5rem;margin-bottom:0.7rem">📊</div>
      <div style="font-size:1rem;font-weight:600;color:#94a3b8;margin-bottom:0.3rem">Drag & drop your dataset here</div>
      <div style="font-size:0.8rem;color:#475569">Supports CSV, XLSX, XLS · Up to 200 MB</div>
    </div>
    """, unsafe_allow_html=True)

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
                missing_counts = full_df.isna().sum()
                missing_df = pd.DataFrame({
                    "Column": missing_counts.index,
                    "Missing Values": missing_counts.values,
                    "Missing %": (missing_counts.values / len(full_df) * 100).round(2),
                    "Data Type": full_df.dtypes.astype(str).values
                }).sort_values("Missing Values", ascending=False)
                
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

    if run_clicked:
        # ── Progress & Logs ──
        st.markdown('<div class="section-header">⚡ <span>Pipeline Execution</span></div>', unsafe_allow_html=True)

        progress_bar = st.progress(0)
        status_box = st.empty()
        log_placeholder = st.empty()

        logs = []
        phase_map = {
            "Phase 1": 8,  "Phase 2": 15, "Phase 3": 22,
            "Phase 4": 30, "Phase 5": 50, "Phase 6": 60,
            "Phase 7": 65, "Phase 8": 75, "Phase 9": 82,
            "Phase 10": 88,"Phase 11": 93,"Phase 12": 97,
            "Completed": 100,
        }

        def log_callback(msg: str):
            logs.append(msg)
            # Update progress
            for key, val in phase_map.items():
                if key in msg:
                    progress_bar.progress(val)
                    break
            # Status chip
            icon = "⚙️"
            if "Completed" in msg:
                icon = "✅"
            elif "Error" in msg or "Failed" in msg:
                icon = "❌"
            status_box.markdown(f"""
            <div class="glass-panel" style="display:flex;align-items:center;gap:10px;padding:0.8rem 1.2rem">
              <span style="font-size:1.1rem">{icon}</span>
              <span style="font-size:0.85rem;color:#94a3b8">{msg}</span>
            </div>
            """, unsafe_allow_html=True)
            # Log box
            log_placeholder.markdown(
                f'<div class="log-box">' + "\n".join(logs[-30:]) + "</div>",
                unsafe_allow_html=True
            )

        # ── Execute ──
        try:
            orchestrator = PipelineOrchestrator(filepath=temp_path, log_callback=log_callback)
            cleaned_df, metadata = orchestrator.execute()
            progress_bar.progress(100)

            # ── SUCCESS BANNER ──
            st.markdown(f"""
            <div class="glass-panel success" style="display:flex;align-items:center;gap:16px;margin-top:1.5rem">
              <div style="font-size:2rem">✨</div>
              <div>
                <div style="font-weight:700;color:#4ade80;font-size:1rem">IntelliClean Pipeline Execution Complete</div>
                <div style="font-size:0.78rem;color:#64748b;margin-top:2px">
                  Processed in {metadata['execution_time_sec']:.1f}s &nbsp;·&nbsp;
                  {metadata['initial_rows']} rows in &nbsp;→&nbsp; {metadata['final_rows']} rows out
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # ── METRICS ROW ──
            validation = metadata.get("validation", {})
            missing_before = sum(v for v in metadata.get("missing_values_before", {}).values() if isinstance(v, (int, float)))
            dedup_count = len(set(c.get("Corrected","") for c in metadata.get("dedup_changes", [])))
            confidence  = validation.get("overall_confidence", 0)
            domain      = metadata.get("domain", "Generic")
            domain_info = metadata.get("domain_info", {})
            domain_conf = domain_info.get("confidence", "")
            domain_method = domain_info.get("method", "")
            domain_reason = domain_info.get("reasoning", "")

            st.markdown(f"""
            <div class="metric-grid">
              <div class="metric-card purple">
                <div class="metric-label">Original Rows</div>
                <div class="metric-value">{metadata['initial_rows']:,}</div>
                <div class="metric-sub">Input dataset size</div>
              </div>
              <div class="metric-card cyan">
                <div class="metric-label">Cleaned Rows</div>
                <div class="metric-value">{metadata['final_rows']:,}</div>
                <div class="metric-sub">After deduplication</div>
              </div>
              <div class="metric-card green">
                <div class="metric-label">AI Confidence</div>
                <div class="metric-value">{confidence:.0f}%</div>
                <div class="metric-sub">Post-cleaning score</div>
              </div>
              <div class="metric-card pink">
                <div class="metric-label">Domain Detected</div>
                <div class="metric-value" style="font-size:1.3rem">{domain}</div>
                <div class="metric-sub">{domain_conf} confidence · {domain_method}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            if domain_reason:
                st.markdown(f"""
                <div class="glass-panel" style="display:flex;align-items:center;gap:10px;padding:0.7rem 1.2rem;margin-bottom:0.5rem">
                  <span style="font-size:1rem">🤖</span>
                  <span style="font-size:0.82rem;color:#94a3b8"><b style="color:#a78bfa">Domain AI Reasoning:</b> {domain_reason}</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── TABBED RESULTS ──
            tab_preview, tab_schema, tab_ml, tab_impute, tab_dedup, tab_currency, tab_audit = st.tabs([
                "📊 Cleaned Data",
                "🧠 Schema Analysis",
                "🌐 Multilingual",
                "🧩 Imputation",
                "🔗 Deduplication",
                "💱 Currency",
                "📋 Audit Trail",
            ])

            # ─ Tab 1: Cleaned Preview ─
            with tab_preview:
                st.markdown('<div class="section-header">📊 <span>Cleaned Dataset</span><span class="section-badge">PREVIEW</span></div>', unsafe_allow_html=True)
                st.dataframe(cleaned_df.head(100), use_container_width=True, height=420)

                # Download row
                st.markdown("<br>", unsafe_allow_html=True)
                dl_col1, dl_col2, dl_col3 = st.columns([1, 1, 1])

                with dl_col1:
                    csv_bytes = cleaned_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥  Download CSV",
                        data=csv_bytes,
                        file_name="intelliclean_output.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

                with dl_col2:
                    try:
                        import io
                        buf = io.BytesIO()
                        cleaned_df.to_excel(buf, index=False, engine="openpyxl")
                        buf.seek(0)
                        st.download_button(
                            label="📊  Download Excel",
                            data=buf.getvalue(),
                            file_name="intelliclean_output.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
                    except Exception:
                        pass

                with dl_col3:
                    exporter = Exporter()
                    rpt_path = exporter.generate_report(metadata)
                    with open(rpt_path, "r", encoding="utf-8") as rf:
                        rpt_bytes = rf.read().encode("utf-8")
                    st.download_button(
                        label="📋  Download Report",
                        data=rpt_bytes,
                        file_name="cleaning_report.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )

            # ─ Tab 2: Schema ─
            with tab_schema:
                st.markdown('<div class="section-header">🧠 <span>AI Column Classification</span></div>', unsafe_allow_html=True)
                schema  = metadata.get("schema_mapping", {})
                strats  = metadata.get("strategies", {})
                if schema:
                    rows = []
                    for col, info in schema.items():
                        strat = strats.get(col, {})
                        rows.append({
                            "Column": col,
                            "Semantic Type": info.get("semantic_type", "?"),
                            "Multilingual": "✅ Yes" if info.get("needs_multilingual") else "— No",
                            "Non-ASCII Ratio": f"{info.get('non_ascii_ratio', 0):.1%}",
                            "Normalization": strat.get("normalization", "none"),
                            "Imputation": info.get("imputation_strategy", strat.get("imputation", "leave_empty")),
                            "AI Reasoning": info.get("imputation_reasoning", ""),
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=350)

                    # Domain intelligence card
                    domain_info = metadata.get("domain_info", {})
                    if domain_info:
                        h_scores = domain_info.get("heuristic_scores", {})
                        top_scores = sorted(h_scores.items(), key=lambda x: x[1], reverse=True)[:5]
                        scores_html = "".join(
                            f'<div style="margin-bottom:5px">'
                            f'<div style="display:flex;justify-content:space-between;font-size:0.75rem;margin-bottom:2px">'
                            f'<span style="color:#94a3b8">{d}</span><span style="color:#64748b">{s}</span></div>'
                            f'<div style="background:rgba(255,255,255,0.04);border-radius:4px;height:6px">'
                            f'<div style="background:linear-gradient(90deg,#7c3aed,#a855f7);border-radius:4px;height:6px;width:{min(s/max(max(h_scores.values()),1)*100,100):.0f}%"></div>'
                            f'</div></div>'
                            for d, s in top_scores
                        )
                        st.markdown(f"""
                        <div class="glass-panel" style="margin-top:1rem">
                          <div style="font-weight:700;color:#e2e8f0;margin-bottom:0.8rem">🌐 Domain Intelligence</div>
                          <div style="display:flex;gap:2rem;margin-bottom:1rem;font-size:0.82rem">
                            <div><span style="color:#64748b">Domain:</span> <b style="color:#a78bfa">{domain_info.get('domain','?')}</b></div>
                            <div><span style="color:#64748b">Confidence:</span> <b style="color:#4ade80">{domain_info.get('confidence','?')}</b></div>
                            <div><span style="color:#64748b">Method:</span> <b style="color:#22d3ee">{domain_info.get('method','?')}</b></div>
                          </div>
                          <div style="font-size:0.78rem;color:#94a3b8;margin-bottom:1rem">💬 {domain_info.get('reasoning','')}</div>
                          <div style="font-size:0.75rem;font-weight:600;color:#64748b;margin-bottom:6px">KEYWORD SCORES</div>
                          {scores_html}
                        </div>
                        """, unsafe_allow_html=True)

                    # Type distribution chips
                    type_counts = {}
                    for col, info in schema.items():
                        t = info.get("semantic_type", "?")
                        type_counts[t] = type_counts.get(t, 0) + 1

                    chips_html = ""
                    color_map = {
                        "Name": "tag-purple", "Categorical": "tag-cyan",
                        "Email": "tag-green", "Phone": "tag-green",
                        "Numeric": "tag-pink" if True else "", "Temporal": "tag-gray",
                        "ID_Code": "tag-gray", "Free_Text": "tag-gray", "Location": "tag-cyan",
                    }
                    for t, c in type_counts.items():
                        color = color_map.get(t, "tag-gray")
                        chips_html += f'<span class="tag {color}">{t}: {c}</span> '
                    st.markdown(chips_html, unsafe_allow_html=True)
                else:
                    st.info("No schema information available.")

            # ─ Tab 3: Multilingual ─
            with tab_ml:
                st.markdown('<div class="section-header">🌐 <span>Multilingual Processing</span></div>', unsafe_allow_html=True)
                stats = metadata.get("translation_stats", {})
                if stats:
                    for col, data in stats.items():
                        task = data.get("task", "Processing")
                        ascii_norm = data.get("ascii_normalized", 0)
                        llm_done   = data.get("llm_translated", data.get("items_processed", 0))
                        mapping    = data.get("mapping", {})
                        changes    = {k: v for k, v in mapping.items() if str(k) != str(v)}

                        task_color = "tag-purple" if "Translit" in task else "tag-cyan"
                        st.markdown(f"""
                        <div class="glass-panel">
                          <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.8rem">
                            <div style="font-weight:700;color:#e2e8f0;font-size:0.9rem">{col}</div>
                            <span class="tag {task_color}">{task}</span>
                          </div>
                          <div style="display:flex;gap:2rem;font-size:0.8rem;color:#64748b">
                            <span>🔡 ASCII normalized: <b style="color:#94a3b8">{ascii_norm}</b></span>
                            <span>🤖 LLM processed: <b style="color:#94a3b8">{llm_done}</b></span>
                            <span>🔄 Values changed: <b style="color:#4ade80">{len(changes)}</b></span>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)

                        if changes:
                            with st.expander(f"View {len(changes)} transformations for '{col}'"):
                                change_rows = [{"Original": k, "→ Cleaned": v} for k, v in list(changes.items())[:50]]
                                st.dataframe(pd.DataFrame(change_rows), use_container_width=True, height=250)
                else:
                    st.markdown("""
                    <div class="glass-panel">
                      <div style="color:#64748b;font-size:0.85rem">No multilingual processing was required — all values were already in English.</div>
                    </div>
                    """, unsafe_allow_html=True)

            # ─ Tab 4: Imputation ─
            with tab_impute:
                st.markdown('<div class="section-header">🧩 <span>Smart Imputation</span></div>', unsafe_allow_html=True)
                rules = metadata.get("smart_imputation_rules", [])
                stats_log = metadata.get("statistical_imputation_log", [])
                missing_before_dict = metadata.get("missing_values_before", {})

                # Missing before grid
                missing_cols = {k: v for k, v in missing_before_dict.items() if v > 0}
                if missing_cols:
                    st.markdown("**Missing Values Before Cleaning:**")
                    chips = "".join(
                        f'<span class="tag tag-red">{c}: {v}</span> '
                        for c, v in missing_cols.items()
                    )
                    st.markdown(chips, unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)

                # Contextual Rules Section
                if rules:
                    st.markdown(f"**{len(rules)} Smart Rules Applied by AI:**")
                    for r in rules:
                        confidence = r.get("confidence", 0)
                        rows_filled = r.get("rows_filled", 0)
                        conf_color = "#4ade80" if confidence >= 80 else "#fbbf24" if confidence >= 60 else "#f87171"
                        st.markdown(f"""
                        <div class="rule-card">
                          <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                            <span style="font-weight:700;color:#a78bfa">{r.get('column','?')}</span>
                            <span style="font-size:0.7rem;color:{conf_color};border:1px solid {conf_color};border-radius:4px;padding:1px 6px">{confidence}% confidence</span>
                            <span class="tag tag-purple" style="font-size:0.65rem">Contextual Rule</span>
                          </div>
                          <div style="color:#94a3b8;font-size:0.82rem">
                            IF <code style="background:rgba(139,92,246,0.15);padding:1px 5px;border-radius:4px;color:#c4b5fd">{r.get('condition','?')}</code>
                            → fill <code style="background:rgba(74,222,128,0.12);padding:1px 5px;border-radius:4px;color:#4ade80">'{r.get('fill_value','?')}'</code>
                            &nbsp;<span style="color:#475569">({rows_filled} rows filled)</span>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="glass-panel">
                      <div style="color:#64748b;font-size:0.85rem">No LLM contextual rules were applied.</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Statistical Fallback Section
                if stats_log:
                    st.markdown(f"**{len(stats_log)} Statistical Fallback Imputations:**")
                    for s in stats_log:
                        strategy = s.get('strategy', '')
                        col = s.get('column', '?')
                        fill_val = s.get('fill_value', '?')
                        rows_filled = s.get('rows_filled', 0)
                        pct = s.get('missing_pct', 0)
                        
                        # Build the extra stats HTML
                        extra_html = ""
                        if strategy in ["fill_mean", "fill_median"]:
                            mean = s.get('mean', '?')
                            median = s.get('median', '?')
                            skew = s.get('skewness', '?')
                            min_val = s.get('min', '?')
                            max_val = s.get('max', '?')
                            extra_html = f"""<div style="display:flex;flex-wrap:wrap;gap:1.5rem;font-size:0.75rem;color:#64748b;margin-top:6px;background:rgba(0,0,0,0.2);padding:8px 10px;border-radius:6px;line-height:1.4">
<div><b style="color:#94a3b8">Mean:</b> {mean}</div>
<div><b style="color:#94a3b8">Median:</b> {median}</div>
<div><b style="color:#94a3b8">Skewness:</b> {skew}</div>
<div><b style="color:#94a3b8">Range:</b> {min_val} to {max_val}</div>
</div>"""
                        elif strategy == "fill_mode":
                            unique = s.get('unique_vals', '?')
                            top_dist = s.get('top_distribution', {})
                            dist_str = " · ".join([f"{k}: {v}" for k, v in top_dist.items()])
                            extra_html = f"""<div style="display:flex;flex-wrap:wrap;gap:1.5rem;font-size:0.75rem;color:#64748b;margin-top:6px;background:rgba(0,0,0,0.2);padding:8px 10px;border-radius:6px;line-height:1.4">
<div><b style="color:#94a3b8">Unique Values:</b> {unique}</div>
<div style="flex:1;min-width:200px;word-break:break-word"><b style="color:#94a3b8">Top Distribution:</b> {dist_str}</div>
</div>"""

                        # Get AI Reasoning for this column
                        schema_mapping = metadata.get("schema_mapping", {})
                        col_schema = schema_mapping.get(col, {})
                        ai_reasoning = col_schema.get("imputation_reasoning", "")
                        
                        reasoning_html = ""
                        if ai_reasoning:
                            reasoning_html = f"""<div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.05);display:flex;align-items:center;gap:8px">
<span style="font-size:0.9rem">🤖</span>
<span style="font-size:0.78rem;color:#a78bfa"><b>AI Reasoning:</b> {ai_reasoning}</span>
</div>"""

                        st.markdown(f"""
                        <div class="glass-panel" style="margin-bottom:0.6rem;padding:0.9rem 1.2rem">
                          <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                            <span style="font-weight:700;color:#22d3ee">{col}</span>
                            <span class="tag tag-cyan" style="font-size:0.65rem">{strategy}</span>
                            <span style="font-size:0.75rem;color:#94a3b8;margin-left:auto">{pct}% missing ({rows_filled} rows)</span>
                          </div>
                          <div style="color:#94a3b8;font-size:0.82rem">
                            Filled with <code style="background:rgba(34,211,238,0.12);padding:1px 5px;border-radius:4px;color:#22d3ee">'{fill_val}'</code>
                          </div>
                          {extra_html}
                          {reasoning_html}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    if not rules:
                        st.markdown("""
                        <div class="glass-panel success">
                          <div style="color:#4ade80;font-weight:600;margin-bottom:4px">✅ Dataset Complete</div>
                          <div style="color:#64748b;font-size:0.82rem">No missing values were found in the dataset.</div>
                        </div>
                        """, unsafe_allow_html=True)

            # ─ Tab 5: Deduplication ─
            with tab_dedup:
                st.markdown('<div class="section-header">🔗 <span>Entity Consolidation & Deduplication</span></div>', unsafe_allow_html=True)
                changes = metadata.get("dedup_changes", [])
                if changes:
                    dedup_df = pd.DataFrame(changes).drop_duplicates().reset_index(drop=True)
                    st.markdown(f'<span class="tag tag-purple">{len(dedup_df)} entities consolidated</span>', unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.dataframe(dedup_df, use_container_width=True, height=350)
                else:
                    st.markdown("""
                    <div class="glass-panel success">
                      <div style="color:#4ade80;font-weight:600;margin-bottom:4px">✅ No duplicates detected</div>
                      <div style="color:#64748b;font-size:0.82rem">All records in your dataset appear to be unique entities.</div>
                    </div>
                    """, unsafe_allow_html=True)

                # Validation issues
                issues = validation.get("issues", [])
                st.markdown('<div class="section-header" style="margin-top:1.5rem">🛡️ <span>Validation Results</span></div>', unsafe_allow_html=True)
                if issues:
                    for issue in issues:
                        st.markdown(f"""
                        <div class="glass-panel warning">
                          <div style="font-size:0.83rem;color:#fbbf24">⚠️ {issue}</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="glass-panel success">
                      <div style="color:#4ade80;font-weight:600">✅ No validation issues found</div>
                      <div style="color:#64748b;font-size:0.82rem">Cleaned dataset passed all post-cleaning quality checks.</div>
                    </div>
                    """, unsafe_allow_html=True)

            # ─ Tab 6: Currency Conversion ─
            with tab_currency:
                st.markdown('<div class="section-header">💱 <span>Currency Detection & Conversion</span></div>', unsafe_allow_html=True)
                currency_report = metadata.get("currency_report", [])
                if currency_report:
                    st.markdown(f"""
                    <div class="glass-panel success" style="display:flex;align-items:center;gap:14px;padding:0.9rem 1.2rem">
                      <div style="font-size:1.8rem">₹</div>
                      <div>
                        <div style="font-weight:700;color:#4ade80;font-size:0.95rem">Currency Conversion Complete</div>
                        <div style="font-size:0.78rem;color:#64748b;margin-top:2px">
                          {len(currency_report)} column(s) detected with mixed currencies &nbsp;·&nbsp; All values converted to <b style="color:#4ade80">INR (₹)</b>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)

                    for cr in currency_report:
                        col_name  = cr.get("column", "?")
                        converted = cr.get("rows_converted", 0)
                        assumed   = cr.get("rows_assumed_inr", 0)
                        failed    = cr.get("rows_failed", 0)
                        rates     = cr.get("rates_used", {})
                        detected  = cr.get("currencies_found", {})

                        # Currency breakdown pills
                        curr_pills = "".join(
                            f'<span class="tag tag-purple" style="font-size:0.68rem">{c}: {cnt} rows</span> '
                            for c, cnt in detected.items()
                        )

                        # Rate display
                        rate_items = "".join(
                            f'<div><b style="color:#94a3b8">1 {c}</b> = <span style="color:#4ade80">₹{r:,.4f}</span></div>'
                            for c, r in rates.items()
                        )

                        st.markdown(f"""
                        <div class="glass-panel" style="margin-bottom:0.8rem">
                          <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
                            <span style="font-weight:700;font-size:1rem;color:#22d3ee">{col_name}</span>
                            <span class="tag tag-cyan">Converted to INR</span>
                          </div>
                          <div style="margin-bottom:8px">{curr_pills}</div>
                          <div style="display:flex;flex-wrap:wrap;gap:2rem;font-size:0.78rem;background:rgba(0,0,0,0.2);padding:8px 12px;border-radius:6px;margin-bottom:8px">
                            {rate_items}
                          </div>
                          <div style="display:flex;gap:1.5rem;font-size:0.75rem;color:#64748b">
                            <div>✅ <b style="color:#4ade80">{converted}</b> rows converted</div>
                            <div>🟡 <b style="color:#fbbf24">{assumed}</b> rows assumed INR (no symbol)</div>
                            <div>{'❌ <b style="color:#f87171">' + str(failed) + '</b> rows unparseable' if failed else ''}</div>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="glass-panel success">
                      <div style="color:#4ade80;font-weight:600;margin-bottom:4px">✅ No currency conversion needed</div>
                      <div style="color:#64748b;font-size:0.82rem">No columns with mixed foreign currencies were detected in your dataset.</div>
                    </div>
                    """, unsafe_allow_html=True)

            # ─ Tab 7: Audit Trail ─
            with tab_audit:
                st.markdown('<div class="section-header">📋 <span>AI Audit Trail</span></div>', unsafe_allow_html=True)
                explanations = metadata.get("explanations", [])
                if explanations:
                    for exp in explanations[:40]:
                        task = exp.get("task", "Transform")
                        task_color = "tag-purple" if "Translit" in task else "tag-cyan"
                        st.markdown(f"""
                        <div class="glass-panel" style="margin-bottom:0.5rem">
                          <div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">
                            <span style="font-weight:600;color:#a78bfa;font-size:0.83rem">{exp.get('column','?')}</span>
                            <span class="tag {task_color}" style="font-size:0.68rem">{task}</span>
                          </div>
                          <div style="font-size:0.8rem;color:#64748b">
                            <code style="background:rgba(248,113,113,0.1);color:#f87171;padding:1px 5px;border-radius:4px">{exp.get('original','?')}</code>
                            &nbsp;→&nbsp;
                            <code style="background:rgba(74,222,128,0.1);color:#4ade80;padding:1px 5px;border-radius:4px">{exp.get('cleaned','?')}</code>
                          </div>
                          <div style="font-size:0.75rem;color:#475569;margin-top:4px">💬 {exp.get('explanation','')}</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="glass-panel">
                      <div style="color:#64748b;font-size:0.85rem">No transformation audit trail was generated for this run.</div>
                    </div>
                    """, unsafe_allow_html=True)

                # Execution log
                st.markdown('<div class="section-header" style="margin-top:1.5rem">📝 <span>Execution Log</span></div>', unsafe_allow_html=True)
                log_text = "\n".join(logs)
                st.markdown(f'<div class="log-box">{log_text}</div>', unsafe_allow_html=True)

        except ConnectionError:
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
