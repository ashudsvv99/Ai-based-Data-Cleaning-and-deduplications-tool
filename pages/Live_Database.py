"""
pages/Live_Database.py — IntelliClean AI · Live Database Studio v3

5-Tab professional UI:
  Tab 1: 🔌 Connect        — DB type selector + connection form
  Tab 2: 🗺️ Database Map   — Table relationships graph + schema cards
  Tab 3: 💬 AI Query Studio — NLP chat console with auto-execute
  Tab 4: 🧹 AI Cleaning    — Full pipeline on live table + write-back
  Tab 5: 📋 Audit Log      — Full query history + backup registry
"""
import os
import json
import time
import datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="IntelliClean · DB Studio",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
#  CSS — Premium dark glassmorphism + chat UI
# ─────────────────────────────────────────────────────────────
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

theme_css = ""
if st.session_state.theme == 'light':
    theme_css = """
/* Light Mode Overrides */
.stApp { background: #fafafa !important; color: #0f172a !important; }
.db-hero { background: linear-gradient(135deg, #f5f5f5 0%, #ffffff 50%, #fafafa 100%) !important; border-color: rgba(139, 92, 246, 0.2) !important; }
.db-hero h1 { background: linear-gradient(135deg, #3b82f6 30%, #8b5cf6 100%) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; }
.db-hero p { color: #475569 !important; }
.db-hero-badge { color: #7c3aed !important; }
.metric-card, .gpanel, .db-card, .chat-container, .upload-zone, .log-container, .rel-graph, .sql-box, .tbl-card, .mini-m, .perm-modal { background: #ffffff !important; border-color: #e2e8f0 !important; color: #1e293b !important; box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important; }
.metric-value, .db-name, .mv { color: #0f172a !important; }
.metric-sub, .metric-label, .db-desc, .ml { color: #64748b !important; }
.sec-hdr, .section-header, h1, h2, h3, h4, h5 { color: #0f172a !important; border-color: #e2e8f0 !important; }
.chat-bubble-user { background: #f3e8ff !important; border-color: #d8b4fe !important; color: #581c87 !important; }
.chat-bubble-ai { background: #fafafa !important; border-color: #e2e8f0 !important; color: #0f172a !important; }
.sql-box { color: #334155 !important; }
.chip { background: #ecfeff !important; border-color: #a5f3fc !important; color: #0e7490 !important; }
.chip:hover { background: #cffafe !important; }
.sec-badge { background: #f3e8ff !important; border-color: #d8b4fe !important; color: #7c3aed !important; }
.tbl-card.active { border-color: #8b5cf6 !important; background: #f5f3ff !important; }
.stTabs [data-baseweb="tab-list"] { background: #e2e8f0 !important; border: 1px solid #cbd5e1 !important; }
.stTabs [data-baseweb="tab"] { color: #475569 !important; }
.stTabs [data-baseweb="tab"]:hover { color: #0f172a !important; background: rgba(0,0,0,0.05) !important; }
.stTabs [aria-selected="true"] { background: #ffffff !important; color: #7c3aed !important; box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important; }
/* Override inline styles */
div[style*="color:#94a3b8"], div[style*="color: #94a3b8"] { color: #64748b !important; }
div[style*="color:#e2e8f0"], div[style*="color: #e2e8f0"] { color: #0f172a !important; }
div[style*="color:#475569"], div[style*="color: #475569"] { color: #475569 !important; }
div[style*="color:#cbd5e1"], div[style*="color: #cbd5e1"] { color: #64748b !important; }
div[style*="color:#a78bfa"], div[style*="color: #a78bfa"] { color: #7c3aed !important; }
div[style*="color:#4ade80"], div[style*="color: #4ade80"] { color: #16a34a !important; }
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #080b14; color: #e2e8f0; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2.5rem 4rem; max-width: 1600px; }

/* ── DB Hero ── */
.db-hero {
    background: linear-gradient(135deg, #1a1040 0%, #0f172a 50%, #0d1a30 100%);
    border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 20px;
    padding: 2rem 2.5rem; margin-bottom: 1.5rem; position: relative; overflow: hidden;
}
.db-hero h1 {
    font-size: 2rem; font-weight: 800; margin: 0.5rem 0;
    background: linear-gradient(135deg, #e2e8f0 30%, #a78bfa 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.db-hero p {
    font-size: 0.9rem; color: #94a3b8; margin-top: 0.4rem; max-width: 700px; line-height: 1.5;
}
.db-hero-badge {
    font-size: 0.72rem; font-weight: 600; color: #a78bfa; letter-spacing: 0.06em; margin-bottom: 0.5rem;
}

/* ── DB type cards ── */
.db-card {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px; padding: 1rem 1.2rem; cursor: pointer;
    transition: all 0.2s; display: flex; flex-direction: column; gap: 5px;
    text-align: center;
}
.db-card:hover { border-color: rgba(139,92,246,0.5); background: rgba(139,92,246,0.07); transform: translateY(-2px); }
.db-card.selected { border-color: #a78bfa; background: rgba(139,92,246,0.14); box-shadow: 0 0 24px rgba(139,92,246,0.22); }
.db-icon { font-size: 1.8rem; }
.db-name { font-size: 0.88rem; font-weight: 700; color: #e2e8f0; }
.db-desc { font-size: 0.7rem; color: #64748b; }

/* ── Connection badges ── */
.conn-ok  { display:inline-flex;align-items:center;gap:5px;background:rgba(74,222,128,0.1);border:1px solid rgba(74,222,128,0.3);border-radius:20px;padding:3px 12px;font-size:0.74rem;font-weight:600;color:#4ade80; }
.conn-err { display:inline-flex;align-items:center;gap:5px;background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);border-radius:20px;padding:3px 12px;font-size:0.74rem;font-weight:600;color:#f87171; }

/* ── Glass panels ── */
.gpanel {
    background: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 1.3rem 1.5rem; margin-bottom: 0.9rem;
}
.gpanel.ok  { border-color:rgba(74,222,128,0.25); background:rgba(74,222,128,0.04); }
.gpanel.warn { border-color:rgba(251,191,36,0.28); background:rgba(251,191,36,0.05); }
.gpanel.err { border-color:rgba(248,113,113,0.25); background:rgba(248,113,113,0.04); }
.gpanel.info { border-color:rgba(34,211,238,0.25); background:rgba(34,211,238,0.04); }
.gpanel.purple { border-color:rgba(139,92,246,0.3); background:rgba(139,92,246,0.06); }

/* ── Section headers ── */
.sec-hdr {
    display:flex;align-items:center;gap:10px;
    font-size:0.95rem;font-weight:700;color:#e2e8f0;
    border-bottom:1px solid rgba(255,255,255,0.07);
    padding-bottom:0.55rem;margin:1.6rem 0 0.9rem;
}
.sec-badge {
    background:rgba(139,92,246,0.15);border:1px solid rgba(139,92,246,0.3);
    border-radius:6px;padding:2px 8px;font-size:0.68rem;font-weight:700;color:#a78bfa;
}

/* ── Relationship graph container ── */
.rel-graph {
    background: rgba(6,8,16,0.9); border: 1px solid rgba(139,92,246,0.2);
    border-radius: 16px; overflow: hidden; min-height: 400px;
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

/* ── Chat UI ── */
.chat-container {
    display: flex; flex-direction: column; gap: 12px;
    max-height: 500px; overflow-y: auto;
    padding: 1rem; background: rgba(6,8,16,0.7);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px; margin-bottom: 1rem;
}
.chat-bubble-user {
    align-self: flex-end; max-width: 75%;
    background: linear-gradient(135deg, rgba(124,58,237,0.35), rgba(139,92,246,0.25));
    border: 1px solid rgba(139,92,246,0.4); border-radius: 18px 18px 4px 18px;
    padding: 0.7rem 1rem; font-size: 0.88rem; color: #e2e8f0;
}
.chat-bubble-ai {
    align-self: flex-start; max-width: 85%;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px 18px 18px 4px; padding: 0.7rem 1rem;
    font-size: 0.88rem; color: #cbd5e1;
}
.chat-meta {
    font-size: 0.68rem; color: #475569; margin-top: 3px;
}
.chat-conf-high { color: #4ade80; }
.chat-conf-med  { color: #fbbf24; }
.chat-conf-low  { color: #f87171; }

/* ── SQL preview ── */
.sql-box {
    background: #060810; border: 1px solid rgba(255,255,255,0.07);
    border-left: 3px solid #a78bfa; border-radius: 10px;
    padding: 0.9rem 1.1rem; font-family: 'Courier New', monospace;
    font-size: 0.82rem; color: #a5f3fc; white-space: pre-wrap;
    overflow-x: auto; margin: 0.4rem 0;
}

/* ── Suggestion chips ── */
.chip {
    display:inline-flex;align-items:center;gap:5px;
    background:rgba(34,211,238,0.07);border:1px solid rgba(34,211,238,0.22);
    border-radius:20px;padding:4px 12px;font-size:0.73rem;font-weight:500;color:#22d3ee;
    cursor:pointer;margin:3px;white-space:nowrap;transition:background 0.15s;
}
.chip:hover { background:rgba(34,211,238,0.18); }

/* ── Permission modal ── */
.perm-modal {
    background: rgba(251,191,36,0.05); border: 1px solid rgba(251,191,36,0.3);
    border-radius: 16px; padding: 1.5rem; margin: 0.8rem 0;
}
.perm-title { font-size: 1rem; font-weight: 700; color: #fbbf24; margin-bottom: 0.5rem; }
.perm-detail { font-size: 0.85rem; color: #94a3b8; line-height: 1.7; }

/* ── Table cards ── */
.tbl-card {
    background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.07);
    border-radius:10px;padding:0.7rem 1rem;margin-bottom:0.45rem;
    display:flex;align-items:center;justify-content:space-between;
    transition:border-color 0.15s;cursor:pointer;
}
.tbl-card:hover  { border-color:rgba(139,92,246,0.4); }
.tbl-card.active { border-color:#a78bfa;background:rgba(139,92,246,0.09); }

/* ── Metric mini-cards ── */
.mini-metrics { display:grid;grid-template-columns:repeat(3,1fr);gap:0.6rem;margin:0.7rem 0; }
.mini-m {
    background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);
    border-radius:10px;padding:0.7rem 1rem;text-align:center;
}
.mini-m .mv { font-size:1.5rem;font-weight:700; }
.mini-m .ml { font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em; }

/* ── Backup badge ── */
.bkp { display:inline-flex;align-items:center;gap:5px;background:rgba(251,191,36,0.09);border:1px solid rgba(251,191,36,0.28);border-radius:8px;padding:3px 9px;font-size:0.72rem;font-weight:600;color:#fbbf24;margin:2px; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background:rgba(255,255,255,0.02) !important; border-radius:12px !important;
    padding:6px !important; border:1px solid rgba(255,255,255,0.05) !important; gap:6px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius:8px !important; padding:9px 18px !important; color:#94a3b8 !important;
    font-weight:600 !important; border:none !important; background:transparent !important;
    transition:all 0.25s !important;
}
.stTabs [data-baseweb="tab"]:hover { color:#e2e8f0 !important; background:rgba(255,255,255,0.05) !important; }
.stTabs [aria-selected="true"] {
    background:linear-gradient(135deg,rgba(139,92,246,0.22),rgba(139,92,246,0.38)) !important;
    color:#c4b5fd !important; box-shadow:0 4px 15px rgba(139,92,246,0.18) !important;
}
/* Sidebar - Hide entirely */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }
button[kind="header"] { display: none !important; }
/* Buttons */
.stButton > button { border-radius:10px !important; font-weight:600 !important; }
.stButton > button[kind="primary"] {
    background:linear-gradient(135deg,#7c3aed,#9333ea) !important;
    border:none !important; color:#fff !important; box-shadow:0 4px 20px rgba(124,58,237,0.38) !important;
}
[data-testid="stDataFrame"] { border-radius:12px; overflow:hidden; }
@keyframes fadeUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
.anim { animation:fadeUp 0.3s ease forwards; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────
from backend.db_connector import DatabaseConnector, DB_TYPES
from agents.nl_query_agent import NLQueryAgent
from agents.llm_client import LMStudioClient

from backend.state_manager import StateManager

# ─────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────
def _init():
    defaults = {
        "db_connector":      None,
        "db_type_sel":       "PostgreSQL",
        "db_params":         {},
        "db_tables":         [],
        "all_schemas":       [],       # [{table, columns, row_count, pk_columns}]
        "relationships":     [],       # discovered FK + inferred links
        "db_overview":       "",
        "active_table":      None,
        "table_schema":      {},
        "table_df":          None,
        "nl_agent":          None,
        "chat_messages":     [],       # [{role, content, sql, result_df, meta}]
        "pending_action":    None,     # destructive query awaiting confirmation
        "cleaning_result":   None,
        "audit_log":         [],
        "suggest_queries":   [],
        "followup_chips":    [],
    }
    
    # Auto-load cached db credentials if starting fresh
    if "db_params" not in st.session_state:
        cached_creds = StateManager.load_db_credentials()
        if cached_creds:
            defaults["db_params"] = cached_creds
            defaults["db_type_sel"] = cached_creds.get("db_type", "PostgreSQL")
            
            # Auto-reconnect!
            connector = DatabaseConnector(cached_creds.get("db_type", "PostgreSQL"), cached_creds)
            ok, msg = connector.connect()
            if ok:
                defaults["db_connector"] = connector
                defaults["nl_agent"] = NLQueryAgent(LMStudioClient())
            
    # Auto-load cached pipeline state if starting fresh
    if "cleaning_result" not in st.session_state:
        df, meta, table, logs = StateManager.load_pipeline_state()
        if df is not None:
            defaults["cleaning_result"] = {"df": df, "meta": meta, "table": table, "logs": logs}
            
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

if st.session_state.db_connector and st.session_state.db_connector.is_connected:
    if not st.session_state.db_tables:
        def _temp_refresh():
            conn = st.session_state.db_connector
            tables = [t for t in conn.list_tables() if not t.endswith("_backup") and "backup_" not in t]
            st.session_state.db_tables = tables
            schemas = []
            for t in tables:
                info = conn.get_table_info(t)
                if info and "columns" in info:
                    schemas.append(info)
            st.session_state.all_schemas = schemas
            agent = st.session_state.nl_agent
            st.session_state.relationships = agent.discover_relationships(conn, schemas) if hasattr(agent, 'discover_relationships') else []
        _temp_refresh()

def _refresh_schema():
    conn = st.session_state.db_connector
    if not conn or not conn.is_connected:
        return
    tables = [t for t in conn.list_tables() if not t.endswith("_backup") and "backup_" not in t]
    st.session_state.db_tables = tables
    schemas = []
    for t in tables:
        info = conn.get_table_info(t)
        if info and "columns" in info:
            schemas.append(info)
    st.session_state.all_schemas = schemas
    # Discover relationships
    agent = st.session_state.nl_agent
    if not agent or not hasattr(agent, 'discover_relationships'):
        agent = NLQueryAgent(LMStudioClient())
        st.session_state.nl_agent = agent
    
    st.session_state.relationships = agent.discover_relationships(conn, schemas)
    # Auto-select first table
    if tables and not st.session_state.active_table:
        st.session_state.active_table = tables[0]
        st.session_state.table_schema = schemas[0] if schemas else {}

def _handle_exec_result(exec_res: dict, query_meta: dict):
    """Process execution result: update chat, audit log, follow-ups."""
    import uuid
    msg_id = str(uuid.uuid4())
    
    if exec_res.get("success"):
        rdf   = exec_res.get("result_df")
        nrows = len(rdf) if rdf is not None else exec_res.get("rows_affected", 0)
        msg   = query_meta.get("explanation", "Query executed successfully.")
        if rdf is None:
            msg += f"\n✅ {nrows} rows affected."
        st.session_state.last_result = exec_res
        st.session_state.chat_messages.append({
            "id": msg_id,
            "role": "assistant",
            "content": msg,
            "confidence": query_meta.get("confidence", "Medium"),
            "success": True,
            "result_df": rdf,
            "rows_affected": nrows,
            "execution_time": exec_res.get("execution_time", 0),
            "sql": query_meta.get("sql", ""),
        })
        # Backups info
        for bk in exec_res.get("backups", []):
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": f"🔒 Backup created: `{bk.get('backup_table','?')}` · CSV: `{bk.get('csv_path','?')}`",
                "confidence": "High",
            })
        # Follow-up suggestions removed as per user request
        st.session_state.followup_chips = []
    else:
        err = exec_res.get("error", "Unknown error")
        err_str = str(err)
        
        # Make error friendly
        friendly_err = err_str
        if "[SQL:" in friendly_err:
            friendly_err = friendly_err.split("[SQL:")[0].strip()
        if "(Background on this error at:" in friendly_err:
            friendly_err = friendly_err.split("(Background on this error at:")[0].strip()
        
        import re
        friendly_err = re.sub(r"^\(.*?\) ", "", friendly_err)
        if friendly_err.startswith("(") and ")" in friendly_err:
            try:
                m = re.search(r',\s*"(.*?)"\)', friendly_err) or re.search(r",\s*'(.*?)'\)", friendly_err)
                if m:
                    friendly_err = m.group(1)
            except Exception:
                pass
                
        friendly_err = friendly_err.strip() or "Unknown database error"
        friendly_err = friendly_err[0].upper() + friendly_err[1:]
        
        friendly_err += " (Check the 👁 View Generated SQL section below to manually fix and run it.)"
        
        exec_res["error"] = friendly_err # Update for UI

        st.session_state.last_result = exec_res
        st.session_state.chat_messages.append({
            "id": msg_id,
            "role": "assistant",
            "content": f"❌ Execution failed: {friendly_err}",
            "confidence": "Low",
            "success": False,
            "error": friendly_err,
            "sql": query_meta.get("sql", ""),
        })

    # Add to audit log
    st.session_state.audit_log.append({
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "table":     st.session_state.active_table,
        "query":     query_meta.get("explanation", "")[:80],
        "sql":       query_meta.get("sql", ""),
        "success":   exec_res.get("success"),
        "rows":      exec_res.get("rows_affected", 0),
        "backups":   exec_res.get("backups", []),
    })

# ─────────────────────────────────────────────────────────────
# Theme & Top Toolbar
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
    if st.button("☀️ Light" if st.session_state.theme == 'dark' else "🌙 Dark", key="btn_theme_live_db", use_container_width=True):
        st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'
        st.rerun()

with col_config:
    if st.button("⚙️ Global Config", use_container_width=True, key="settings_btn_live"):
        from components.settings_modal import render_settings_modal
        render_settings_modal()

with col_status:
    st.markdown(f"<div style='display:flex; justify-content:flex-end; padding-top:2px'>{indicator_html}</div>", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────
is_conn = bool(st.session_state.db_connector and st.session_state.db_connector.is_connected)

st.markdown("""
<div class="db-hero">
  <div class="db-hero-badge">
    🗄️ INTELLICLEAN AI · LIVE DATABASE STUDIO
  </div>
  <h1>
    Universal Database Cleaning & Query Studio
  </h1>
  <p>
    Connect to any SQL database • Explore relationships • Query in plain English •
    AI-powered data cleaning • Full audit trail
  </p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 5 Main Tabs
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔌 Connect",
    "🗺️ Database Map",
    "📊 Data Health Profile",
    "💬 AI Query Studio",
    "🧹 AI Cleaning",
    "📋 Audit Log",
])

# ═══════════════════════════════════════════════════════════════
# TAB 1 — CONNECT
# ═══════════════════════════════════════════════════════════════
with tab1:
    col_left, col_right = st.columns([2.5, 1.5], gap="large")
    
    with col_left:
        # ── DB type selector ──
        st.markdown('<div class="sec-hdr">🔌 <span>Select Database</span></div>', unsafe_allow_html=True)
        db_names = list(DB_TYPES.keys())
        for row_start in range(0, len(db_names), 3):
            row_dbs = db_names[row_start:row_start+3]
            cols = st.columns(len(row_dbs))
            for i, db_name in enumerate(row_dbs):
                meta = DB_TYPES[db_name]
                is_sel = st.session_state.db_type_sel == db_name
                is_connected_db = is_conn and st.session_state.db_connector.db_type == db_name
                
                cls = "db-card selected" if is_sel else "db-card"
                with cols[i]:
                    connected_badge = '<div style="margin-top:5px"><span class="conn-ok">✅ connected</span></div>' if is_connected_db else ''
                    st.markdown(f"""
                    <div class="{cls}">
                      <div class="db-icon">{meta['icon']}</div>
                      <div class="db-name">{db_name}</div>
                      <div class="db-desc">{meta['description']}</div>
                      {connected_badge}
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("Select", key=f"sel_{db_name}", use_container_width=True):
                        st.session_state.db_type_sel = db_name
                        st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

    with col_right:
        db_type = st.session_state.db_type_sel
        meta    = DB_TYPES[db_type]
        is_connected_db = is_conn and st.session_state.db_connector.db_type == db_type

        if is_connected_db:
            c = st.session_state.db_connector.get_connection_summary()
            st.markdown(
                f'<div class="sec-hdr">{meta["icon"]} <span>{db_type}</span>'
                f'<span class="sec-badge">ACTIVE</span></div>',
                unsafe_allow_html=True
            )
            st.markdown(f"""
            <div class="gpanel ok anim" style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem;">
              <div>
                <div style="font-weight:800;color:#4ade80;font-size:1.4rem">✅ Connected</div>
                <div style="color:#94a3b8;margin-top:4px">{c.get('host','') or ''} · DB: <b>{c['database']}</b></div>
              </div>
              <div>
                <div style="color:#64748b;font-size:0.8rem;text-transform:uppercase">Tables Found</div>
                <div style="color:#a78bfa;font-weight:700;font-size:2rem">{len(st.session_state.db_tables)}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            col_refresh, col_disc = st.columns(2)
            with col_refresh:
                if st.button("🔄 Refresh Schema", use_container_width=True):
                    _refresh_schema()
                    st.rerun()
            with col_disc:
                if st.button("🔌 Disconnect", type="primary", use_container_width=True):
                    st.session_state.db_connector.disconnect()
                    StateManager.clear_db_credentials()
                    for k in ["db_connector","db_tables","all_schemas","active_table","table_schema","table_df","relationships","db_overview"]:
                        st.session_state[k] = [] if isinstance(st.session_state.get(k), list) else None
                    st.rerun()
        else:
            # ── Connection form ──
            st.markdown(
                f'<div class="sec-hdr">{meta["icon"]} <span>{db_type} Connection</span>'
                f'<span class="sec-badge">CONFIGURE</span></div>',
                unsafe_allow_html=True
            )

            with st.form("db_connect_form"):
                params = {}

                if db_type == "SQLite":
                    params["filepath"] = st.text_input(
                        "Database File Path",
                        value=st.session_state.db_params.get("filepath", ""),
                        placeholder="C:/path/to/database.db  or  :memory:"
                    )
                else:
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        params["host"] = st.text_input("Host",
                            value=st.session_state.db_params.get("host", ""),
                            placeholder="db.example.com or localhost")
                    with c2:
                        params["port"] = st.text_input("Port",
                            value=st.session_state.db_params.get("port", str(meta["default_port"] or "")))

                    params["database"] = st.text_input("Database Name",
                        value=st.session_state.db_params.get("database", ""),
                        placeholder="my_database")
                    params["username"] = st.text_input("Username",
                        value=st.session_state.db_params.get("username", ""))
                    params["password"] = st.text_input("Password", type="password",
                        value=st.session_state.db_params.get("password", ""))

                    if db_type == "PostgreSQL":
                        params["ssl_mode"] = st.selectbox("SSL Mode",
                            ["disable", "require", "verify-ca", "verify-full"],
                            index=["disable","require","verify-ca","verify-full"].index(
                                st.session_state.db_params.get("ssl_mode", "disable") if st.session_state.db_params.get("ssl_mode", "disable") in ["disable","require","verify-ca","verify-full"] else "disable"))
                    if db_type == "SQL Server":
                        params["odbc_driver"] = st.text_input("ODBC Driver",
                            value=st.session_state.db_params.get("odbc_driver", "ODBC Driver 17 for SQL Server"))
                    if db_type == "Snowflake":
                        params["schema"] = st.text_input("Schema",
                            value=st.session_state.db_params.get("schema", ""),
                            placeholder="PUBLIC")
                        params["warehouse"] = st.text_input("Warehouse",
                            value=st.session_state.db_params.get("warehouse", ""))
                        params["role"] = st.text_input("Role",
                            value=st.session_state.db_params.get("role", ""))

                with st.expander("⚙️ Advanced Options"):
                    params["pool_size"] = st.number_input("Connection Pool Size", 1, 20, 5)
                    params["timeout"]   = st.number_input("Query Timeout (s)", 5, 600, 30)
                    params["read_only"] = st.checkbox("Read-Only Mode (no write-back)", value=False)

                c_test, c_save = st.columns(2)
                with c_test:
                    test_btn = st.form_submit_button("⚡ Test", use_container_width=True)
                with c_save:
                    save_btn = st.form_submit_button("💾 Connect", type="primary", use_container_width=True)

            if test_btn or save_btn:
                st.session_state.db_params = params
                connector = DatabaseConnector(db_type, params)
                ok, msg = connector.connect()
                if ok:
                    st.session_state.db_connector = connector
                    st.session_state.nl_agent     = NLQueryAgent(LMStudioClient())
                    _refresh_schema()
                    if save_btn:
                        save_params = params.copy()
                        save_params["db_type"] = db_type
                        StateManager.save_db_credentials(save_params)
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.success(f"✅ {msg} — click **Connect** to proceed.")
                else:
                    st.error(f"❌ {msg}")


# ═══════════════════════════════════════════════════════════════
# TAB 2 — DATABASE MAP
# ═══════════════════════════════════════════════════════════════
with tab2:
    if not is_conn:
        st.info("🔌 Connect to a database first (Tab 1) to see the database map.")
    else:
        # ── Interactive Knowledge Graph ──
        col_hdr, col_btn = st.columns([4, 1])
        with col_hdr:
            st.markdown('<div class="sec-hdr">🗺️ <span>Interactive Knowledge Graph</span></div>', unsafe_allow_html=True)
        with col_btn:
            if st.button("🔄 Refresh Graph", use_container_width=True):
                st.session_state.extended_metadata = None
                st.rerun()

        if "extended_metadata" not in st.session_state or st.session_state.extended_metadata is None:
            with st.spinner("Discovering deep metadata (Keys, Views, Triggers, Functions)..."):
                if hasattr(st.session_state.db_connector, "get_extended_metadata"):
                    st.session_state.extended_metadata = st.session_state.db_connector.get_extended_metadata()
                else:
                    st.warning("⚠️ Application updated. Please click 'Connect' again in Tab 1 to refresh the connection object.")
                    st.session_state.extended_metadata = {"error": "Connection object out of date due to hot-reload. Reconnect in Tab 1."}

        if "expanded_nodes" not in st.session_state:
            st.session_state.expanded_nodes = set()

        ext_meta = st.session_state.extended_metadata
        if "error" in ext_meta:
            st.error(f"Error fetching metadata: {ext_meta['error']}")
        else:
            try:
                from streamlit_agraph import agraph, Node, Edge, Config
                nodes = []
                edges = []
                
                # Helper to safely add node and track IDs
                node_ids = set()
                def add_node(n):
                    if n.id not in node_ids:
                        nodes.append(n)
                        node_ids.add(n.id)
                
                tables = ext_meta.get("tables", [])
                table_names = {t["name"] for t in tables}
                
                # Extract PKs and FKs for quick lookup
                pk_dict = {}
                for pk in ext_meta.get("primary_keys", []):
                    pk_dict[pk["table"]] = pk.get("columns", [])
                
                fk_dict = {}
                dependencies = {t["name"]: [] for t in tables}
                
                for fk in ext_meta.get("foreign_keys", []):
                    tname = fk["table"]
                    if tname not in fk_dict:
                        fk_dict[tname] = []
                    fk_dict[tname].append(fk)
                    
                    target = fk["referred_table"]
                    if target in table_names:
                        dependencies[tname].append(target)
                        
                # Compute hierarchical levels for tables (Main vs Sub-main)
                levels = {}
                def get_level(t):
                    if t in levels: return levels[t]
                    deps = dependencies.get(t, [])
                    if not deps:
                        levels[t] = 0
                        return 0
                    levels[t] = 0 # break cycles
                    max_dep = -1
                    for d in deps:
                        max_dep = max(max_dep, get_level(d))
                    levels[t] = max_dep + 1
                    return levels[t]
                
                for t in tables:
                    get_level(t["name"])
                
                # Dynamic Colors for Main vs Sub-main (Option 1: Modern & Vibrant)
                level_styles = [
                    {"bg": "#3B82F6", "border": "#60A5FA"}, # Blue
                    {"bg": "#8B5CF6", "border": "#A78BFA"}, # Purple
                    {"bg": "#EC4899", "border": "#F472B6"}, # Pink
                    {"bg": "#14B8A6", "border": "#5EEAD4"}  # Teal
                ]
                
                # Helper for consistent fonts
                white_font = {"color": "#FFFFFF"}
                black_font = {"color": "#000000"}
                col_font = {"color": "#F8FAFC"}
                edge_font = {"color": "#94a3b8", "size": 11, "strokeWidth": 0} # No white stroke
                
                # 1. Base Nodes
                for t in tables:
                    t_id = f"TABLE_{t['name']}"
                    lvl = levels.get(t['name'], 0)
                    style = level_styles[min(lvl, len(level_styles)-1)]
                    size = max(20, 35 - (lvl * 4)) # Main tables are larger
                    
                    add_node(Node(id=t_id, 
                                  label=t['name'], 
                                  size=size, 
                                  shape="database", 
                                  color={"background": style["bg"], "border": style["border"], "highlight": style["border"]},
                                  font={"color": "#FFFFFF", "size": 16, "bold": True},
                                  title=f"Table Level: {lvl} (Main)" if lvl == 0 else f"Table Level: {lvl} (Sub-main)"))
                    
                for v in ext_meta.get("views", []):
                    add_node(Node(id=f"VIEW_{v['name']}", 
                                  label=v['name'], 
                                  size=25, 
                                  shape="hexagon", 
                                  color={"background": "#9333ea", "border": "#d8b4fe"}, 
                                  font=white_font))
                
                # 3. Process each table for edges & expansions
                for t in tables:
                    tname = t["name"]
                    t_id = f"TABLE_{tname}"
                    is_expanded = t_id in st.session_state.expanded_nodes
                    
                    table_fks = fk_dict.get(tname, [])
                    table_pks = pk_dict.get(tname, [])
                    
                    for fk in table_fks:
                        fk_name = fk["name"]
                        target_tname = fk["referred_table"]
                        
                        if is_expanded:
                            fk_id = f"FK_{tname}_{fk_name}"
                            # Add FK node (Emerald Green)
                            add_node(Node(id=fk_id, label=f"FK: {target_tname}", title=f"Foreign Key referencing {target_tname}", 
                                          size=15, shape="box", 
                                          color={"background": "#10B981", "border": "#34D399"}, font=black_font))
                            edges.append(Edge(source=t_id, target=fk_id, label="FK", color="#475569", font=edge_font))
                            
                            # Edge from FK node to Target Table
                            if target_tname in table_names:
                                target_id = f"TABLE_{target_tname}"
                                edges.append(Edge(source=fk_id, target=target_id, label="ref", color="#475569", font=edge_font))
                            elif target_tname:
                                # Broken Reference! Red node
                                missing_id = f"MISSING_{target_tname}"
                                add_node(Node(id=missing_id, label=f"? {target_tname}", size=20, shape="database", 
                                              color={"background": "#dc2626", "border": "#fca5a5"}, font=white_font, title="Broken Reference"))
                                edges.append(Edge(source=fk_id, target=missing_id, label="broken", color="#ef4444", font=edge_font))
                        else:
                            # Not expanded, just draw direct Table -> Table edge
                            if target_tname in table_names:
                                target_id = f"TABLE_{target_tname}"
                                edges.append(Edge(source=t_id, target=target_id, label="FK", color="#475569", font=edge_font))
                            elif target_tname:
                                missing_id = f"MISSING_{target_tname}"
                                add_node(Node(id=missing_id, label=f"? {target_tname}", size=20, shape="database", 
                                              color={"background": "#dc2626", "border": "#fca5a5"}, font=white_font, title="Broken Reference"))
                                edges.append(Edge(source=t_id, target=missing_id, label="broken", color="#ef4444", font=edge_font))
                                
                    if is_expanded:
                        # Show PKs (Amber/Gold)
                        for c in table_pks:
                            pk_id = f"PK_{tname}_{c}"
                            add_node(Node(id=pk_id, label=f"PK: {c}", size=15, shape="box", 
                                          color={"background": "#F59E0B", "border": "#FCD34D"}, font=black_font, title="Primary Key"))
                            edges.append(Edge(source=t_id, target=pk_id, label="PK", color="#475569", font=edge_font))
                            
                        # Show regular columns (Slate Grey Ellipse)
                        cols = [c for c in ext_meta.get("columns", []) if c["table"] == tname]
                        for c in cols:
                            cname = c["name"]
                            if cname not in table_pks:
                                col_id = f"COL_{tname}_{cname}"
                                col_type = c.get("type", "unknown")
                                add_node(Node(id=col_id, label=cname, title=f"Type: {col_type}", 
                                              size=12, shape="ellipse", 
                                              color={"background": "#334155", "border": "#475569"}, font=col_font))
                                edges.append(Edge(source=t_id, target=col_id, label="col", color="#475569", font=edge_font))
    
                config = Config(width='100%', 
                                height=800, 
                                directed=True,
                                physics=True, 
                                hierarchical=False,
                                nodeHighlightBehavior=True,
                                highlightColor="#facc15",
                                linkLength=120,
                                **{
                                    "interaction": {
                                        "navigationButtons": True,
                                        "zoomView": True,
                                        "dragView": True
                                    }
                                })

    
                if len(nodes) == 0:
                    st.info("No extended schema objects found to display. The database might be empty or missing permissions.")
                else:
                    return_value = agraph(nodes=nodes, edges=edges, config=config)
                    
                    if "last_clicked_node" not in st.session_state:
                        st.session_state.last_clicked_node = None
                        
                    if return_value != st.session_state.last_clicked_node:
                        st.session_state.last_clicked_node = return_value
                        if return_value and isinstance(return_value, str) and return_value.startswith("TABLE_"):
                            if return_value in st.session_state.expanded_nodes:
                                st.session_state.expanded_nodes.remove(return_value)
                            else:
                                st.session_state.expanded_nodes.add(return_value)
                            import time
                            time.sleep(0.15) # Prevents iframe websocket crash
                            st.rerun()
                        
            except ImportError:
                st.error("Please install streamlit-agraph (`pip install streamlit-agraph`) to view the Knowledge Graph.")

        # ── Table summary cards ──────────────────────────────────
        st.markdown('<div class="sec-hdr">📋 <span>Table Summaries</span></div>', unsafe_allow_html=True)
        conn = st.session_state.db_connector
        schemas = st.session_state.all_schemas
        for i in range(0, len(schemas), 3):
            row_schemas = schemas[i:i+3]
            cols = st.columns(len(row_schemas))
            for j, schema in enumerate(row_schemas):
                with cols[j]:
                    tname  = schema["table"]
                    ncols  = len(schema.get("columns", []))
                    nrows  = schema.get("row_count", "?")
                    pk     = ", ".join(schema.get("pk_columns", [])) or "none"
                    st.markdown(f"""
                    <div class="gpanel purple" style="min-height:130px; margin-bottom:2px; border-bottom-left-radius:4px; border-bottom-right-radius:4px;">
                      <div style="font-weight:700;color:#a78bfa;font-size:1rem;margin-bottom:6px">📋 {tname}</div>
                      <div style="font-size:0.78rem;color:#94a3b8;display:grid;gap:3px">
                        <span>Rows: <b style="color:#e2e8f0">{nrows}</b></span>
                        <span>Columns: <b style="color:#e2e8f0">{ncols}</b></span>
                        <span>PK: <b style="color:#22d3ee">{pk}</b></span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("🔍 Explore", key=f"exp_{tname}", use_container_width=True):
                        st.session_state.active_table  = tname
                        st.session_state.table_schema  = schema
                        try:
                            st.session_state.table_df = conn.load_table(tname, limit=500)
                        except Exception:
                            st.session_state.table_df = None
                        st.rerun()

        # ── Selected table preview ───────────────────────────────
        if st.session_state.active_table and st.session_state.table_df is not None:
            st.markdown(f'<div class="sec-hdr">🔎 <span>Preview: {st.session_state.active_table}</span></div>',
                        unsafe_allow_html=True)
            tdf = st.session_state.table_df
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                st.markdown(f'<div class="mini-m"><div class="mv" style="color:#a78bfa">{len(tdf)}</div><div class="ml">Rows Loaded</div></div>', unsafe_allow_html=True)
            with mc2:
                null_pct = round(tdf.isna().mean().mean() * 100, 1)
                col = "#f87171" if null_pct > 10 else "#4ade80"
                st.markdown(f'<div class="mini-m"><div class="mv" style="color:{col}">{null_pct}%</div><div class="ml">Null Rate</div></div>', unsafe_allow_html=True)
            with mc3:
                # ── Exact duplicate detection: exclude PK columns, normalize NULLs ──
                try:
                    _prev_tbl  = st.session_state.active_table
                    _prev_conn = st.session_state.db_connector
                    # Detect PK columns to exclude from comparison
                    _p_info = _prev_conn.get_table_info(_prev_tbl)
                    _p_all  = [c["name"] for c in _p_info.get("columns", [])]
                    _p_pks  = set(_p_info.get("pk_columns", []))
                    if not _p_pks:
                        _p_pks = {
                            c for c in _p_all
                            if c.lower() in ("id", "pk") or
                               c.lower().endswith("_id") or
                               c.lower().startswith("id_")
                        }
                    _p_data_cols = [c for c in _p_all if c not in _p_pks] or _p_all
                    if _prev_conn.db_type == "MySQL":
                        _pcol_list = ", ".join([f"`{c}`" for c in _p_data_cols])
                        _pdup_sql = (
                            f"SELECT COALESCE(SUM(cnt - 1), 0) FROM "
                            f"(SELECT {_pcol_list}, COUNT(*) as cnt FROM `{_prev_tbl}` "
                            f"GROUP BY {_pcol_list} HAVING COUNT(*) > 1) AS dupes"
                        )
                    else:
                        _pcol_list = ", ".join([f'"{c}"' for c in _p_data_cols])
                        _pdup_sql = (
                            f'SELECT COALESCE(SUM(cnt - 1), 0) FROM '
                            f'(SELECT {_pcol_list}, COUNT(*) as cnt FROM "{_prev_tbl}" '
                            f'GROUP BY {_pcol_list} HAVING COUNT(*) > 1) AS dupes'
                        )
                    _pdup_res, _pdup_err = _prev_conn.execute_query(_pdup_sql)
                    _sql_val = _pdup_res.iloc[0, 0] if (_pdup_err is None and _pdup_res is not None and len(_pdup_res) > 0) else None
                    exact_dupe_count = int(_sql_val) if _sql_val is not None else 0
                except Exception:
                    # Pandas fallback: exclude PK cols present in loaded df
                    try:
                        _tdf_pk = {
                            c for c in tdf.columns
                            if c.lower() in ("id", "pk") or
                               c.lower().endswith("_id") or
                               c.lower().startswith("id_")
                        }
                        _tdf_data = [c for c in tdf.columns if c not in _tdf_pk] or list(tdf.columns)
                        _NULL_R = {"none", "nan", "nat", "null", "", "na", "n/a"}
                        _tdf_n  = tdf[_tdf_data].applymap(lambda v: "__NULL__" if str(v).strip().lower() in _NULL_R else str(v).strip().lower())
                        exact_dupe_count = int(_tdf_n.duplicated().sum())
                    except Exception:
                        exact_dupe_count = 0
                dupe_col = "#f87171" if exact_dupe_count > 0 else "#4ade80"
                st.markdown(f'<div class="mini-m"><div class="mv" style="color:{dupe_col}">{exact_dupe_count}</div><div class="ml">Exact Dupes</div></div>', unsafe_allow_html=True)
            st.dataframe(tdf.head(100), use_container_width=True, height=300)


# ═══════════════════════════════════════════════════════════════
# TAB 3 — DATA HEALTH PROFILE
with tab3:
    if not is_conn:
        st.info("🔌 Connect to a database first (Tab 1) to run the data health profile.")
    else:
        from components.data_health_ui import render_data_health_profile
        render_data_health_profile(
            st.session_state.db_connector,
            st.session_state.db_tables if st.session_state.db_tables else [],
            st.session_state.active_table
        )


# TAB 4 — AI QUERY STUDIO (NLP Chat Console)
# ═══════════════════════════════════════════════════════════════
with tab4:
    if not is_conn:
        st.info("🔌 Connect to a database first (Tab 1) to use the AI Query Studio.")
    else:
        agent  = st.session_state.nl_agent
        conn   = st.session_state.db_connector
        tables = st.session_state.db_tables

        # ── Table selector ───────────────────────────────────────
        left_col, right_col = st.columns([1, 2], gap="large")

        with left_col:
            st.markdown('<div class="sec-hdr">📋 <span>Tables</span></div>', unsafe_allow_html=True)
            for tbl in tables:
                is_active = st.session_state.active_table == tbl
                cls = "tbl-card active" if is_active else "tbl-card"
                st.markdown(f'<div class="{cls}" style="font-size:0.83rem"><span>📋 {tbl}</span></div>',
                            unsafe_allow_html=True)
                if st.button("Select", key=f"sel_tbl_{tbl}", use_container_width=True):
                    st.session_state.active_table = tbl
                    # Find schema
                    for s in st.session_state.all_schemas:
                        if s["table"] == tbl:
                            st.session_state.table_schema = s
                            break
                    try:
                        st.session_state.table_df = conn.load_table(tbl, limit=500)
                    except Exception:
                        st.session_state.table_df = None
                    agent.clear_conversation()
                    st.session_state.chat_messages = []
                    st.session_state.followup_chips = []
                    st.session_state.pending_action = None
                    st.rerun()

            st.divider()
            if st.button("🗑️ Clear Chat", use_container_width=True):
                agent.clear_conversation()
                st.session_state.chat_messages = []
                st.session_state.followup_chips = []
                st.session_state.pending_action = None
                st.rerun()

            # ── Always-visible Quick Actions ──
            st.markdown('<div class="sec-hdr">⚡ <span>Quick Actions</span></div>', unsafe_allow_html=True)
            _quick_actions = [
                ("🔍 Check all issues",       "Check this table for all types of issues"),
                ("👯 Find exact duplicates",  "Find exact duplicate rows"),
                ("❓ Count nulls per column", "How many null values in each column?"),
                ("📊 Show table summary",     "Show summary statistics for this table"),
                ("🔢 Show top 10 rows",       "Show top 10 rows"),
                ("📈 Row count",              "How many total rows are in this table?"),
            ]
            for _qa_label, _qa_prompt in _quick_actions:
                if st.button(_qa_label, key=f"qa_{_qa_label}", use_container_width=True):
                    st.session_state._run_query_nl = _qa_prompt
                    st.rerun()

            st.divider()
            # Dynamic AI-generated suggestions
            if st.session_state.suggest_queries:
                st.markdown('<div class="sec-hdr">🤖 <span>AI Suggestions</span></div>', unsafe_allow_html=True)
                for q in st.session_state.suggest_queries[:6]:
                    lbl = q.get("label", "Query")[:32]
                    cat = q.get("category", "")
                    if st.button(f"{'🔁' if cat=='Duplicates' else '⚠️' if cat=='Missing Values' else '📊'} {lbl}",
                                 key=f"qsug_{lbl}", use_container_width=True):
                        st.session_state._run_query_nl = lbl
                        st.rerun()

        with right_col:
            active_tbl    = st.session_state.active_table
            table_schema  = st.session_state.table_schema
            db_type       = st.session_state.db_connector.db_type

            if not active_tbl:
                st.info("← Select a table on the left to start querying.")
            else:
                st.markdown(f"""
                <div style="font-size:0.85rem;color:#64748b;margin-bottom:0.8rem">
                  Querying: <b style="color:#a78bfa">{active_tbl}</b>
                  · {table_schema.get('row_count','?')} rows
                  · {len(table_schema.get('columns',[]))} columns
                </div>
                """, unsafe_allow_html=True)

                # ── Chat history ─────────────────────────────────
                if not st.session_state.chat_messages:
                    st.markdown(
                        '<div style="text-align:center;color:#475569;padding:2rem;font-size:0.85rem">'
                        '💬 Ask anything in plain English about your data.<br>'
                        '<span style="font-size:0.75rem">'
                        '"Check this table for all types of issues" · '
                        '"Find duplicate emails" · "How many nulls in each column?"<br>'
                        '"Show rows where name is empty" · "Count total rows"'
                        '</span>'
                        '</div>', unsafe_allow_html=True
                    )
                else:
                    for i, msg in enumerate(st.session_state.chat_messages):
                        if msg["role"] == "user":
                            st.markdown(f'<div class="chat-bubble-user" style="margin-bottom: 1rem;">{msg["content"]}</div>', unsafe_allow_html=True)
                        else:
                            conf = msg.get("confidence", "Medium")
                            conf_cls = "chat-conf-high" if conf=="High" else "chat-conf-med" if conf=="Medium" else "chat-conf-low"
                            st.markdown(
                                f'<div class="chat-bubble-ai" style="margin-bottom: 10px;">'
                                f'<div>{msg["content"]}</div>'
                                f'<div class="chat-meta"><span class="{conf_cls}">● {conf}</span></div>'
                                f'</div>', 
                                unsafe_allow_html=True
                            )
                            
                            # Result display inline
                            if "success" in msg:
                                if msg.get("success"):
                                    rdf = msg.get("result_df")
                                    if rdf is not None:
                                        if len(rdf) > 0:
                                            st.markdown(f'<div style="font-size:0.75rem;color:#64748b;margin-bottom:4px">'
                                                        f'✓ {len(rdf)} rows returned · {msg.get("execution_time",0):.2f}s</div>',
                                                        unsafe_allow_html=True)
                                            st.dataframe(rdf, use_container_width=True, height=min(350, 35*len(rdf)+40))
                                        else:
                                            st.info(f"✅ Query executed successfully in {msg.get('execution_time',0):.2f}s, but returned 0 rows.")
                                    else:
                                        st.success(f"✅ Query executed successfully. {msg.get('rows_affected', 0)} rows affected.")
                                else:
                                    if msg.get("error"):
                                        st.error(f"❌ {msg['error']}")
                            
                            # SQL Form inline
                            if msg.get("sql"):
                                is_error = not msg.get("success", True)
                                msg_id = msg.get("id", str(i))
                                with st.expander("👁 View Generated SQL", expanded=is_error):
                                    with st.form(f"edit_sql_form_{msg_id}"):
                                        edited_sql = st.text_area("SQL Query", value=msg["sql"], height=150, label_visibility="collapsed")
                                        cols = st.columns([4, 1])
                                        with cols[1]:
                                            submit_edit = st.form_submit_button("▶ Run", type="primary", use_container_width=True)
                                    if submit_edit and edited_sql.strip():
                                        with st.spinner("⚡ Executing edited SQL..."):
                                            query_meta = {
                                                "sql": edited_sql,
                                                "explanation": "Manually executed query.",
                                                "confidence": "High",
                                                "user_query": "Manual execution",
                                            }
                                            exec_res = agent.execute_with_backup(
                                                conn, edited_sql, query_meta,
                                                backup_dir=os.path.join(os.getcwd(), "exports"),
                                                user_query=None,
                                                table_schema=table_schema,
                                            )
                                        _handle_exec_result(exec_res, query_meta)
                                        st.rerun()



                # ── Permission modal for destructive queries ──────
                if st.session_state.pending_action:
                    pa = st.session_state.pending_action
                    st.markdown(f"""
                    <div class="perm-modal">
                      <div class="perm-title">⚠️ Permission Required — Destructive Operation</div>
                      <div class="perm-detail">
                        <b>Operation:</b> {pa.get('intent_type','write').upper()}<br>
                        <b>Affects tables:</b> {', '.join(pa.get('affected_tables',[]))}<br>
                        <b>Explanation:</b> {pa.get('explanation','')}<br>
                        <b>Safety note:</b> {pa.get('safety_warning','')}<br><br>
                        ✅ A backup will be created automatically before execution.
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Show SQL for destructive ops
                    with st.expander("👁 View SQL to be Executed", expanded=True):
                        st.code(pa.get("sql", ""), language="sql")

                    conf_col, cancel_col = st.columns(2)
                    with conf_col:
                        if st.button("✅ Confirm & Execute", type="primary", use_container_width=True, key="perm_confirm"):
                            with st.spinner("⚙️ Creating backup and executing..."):
                                exec_res = agent.execute_with_backup(
                                    conn, pa["sql"], pa,
                                    backup_dir=os.path.join(os.getcwd(), "exports"),
                                    user_query=pa.get("user_query",""),
                                    table_schema=table_schema,
                                )
                            st.session_state.pending_action = None
                            _handle_exec_result(exec_res, pa)
                            st.rerun()
                    with cancel_col:
                        if st.button("❌ Cancel", use_container_width=True, key="perm_cancel"):
                            st.session_state.pending_action = None
                            st.session_state.chat_messages.append({
                                "role": "assistant",
                                "content": "❌ Operation cancelled. No changes were made.",
                                "confidence": "High",
                            })
                            st.rerun()

                # ── Input bar ─────────────────────────────────────
                with st.form("nl_query_form", clear_on_submit=True):
                    user_input = st.text_input(
                        "Ask about your data",
                        placeholder="e.g. Show top 5 rows · Find all duplicate emails · Check this table for all types of issues · Count nulls per column",
                        label_visibility="collapsed",
                    )
                    submitted = st.form_submit_button("▶ Send", type="primary", use_container_width=False)

                if submitted and user_input.strip():
                    st.session_state._run_query_nl = user_input.strip()
                    st.rerun()

                # ── Query execution ────────────────────────────────
                if st.session_state.get("_run_query_nl"):
                    query_text = st.session_state.pop("_run_query_nl")
                    st.session_state.chat_messages.append({"role": "user", "content": query_text})

                    # ── Detect 'check all issues' intent for comprehensive analysis ──
                    _COMPREHENSIVE_TRIGGERS = [
                        "all types of issues", "all issues", "check this table", "full analysis",
                        "comprehensive check", "data quality check", "health check", "audit this table",
                        "what issues", "what problems", "data problems", "find all problems",
                        "scan this table", "inspect this table", "quality report", "analyse this table",
                        "analyze this table",
                    ]
                    _is_comprehensive = any(t in query_text.lower() for t in _COMPREHENSIVE_TRIGGERS)

                    if _is_comprehensive and active_tbl:
                        # Run multi-query comprehensive analysis
                        with st.spinner("🔍 Running comprehensive data quality analysis..."):
                            _comp_results = []
                            _comp_conn = conn
                            _db_t = db_type

                            def _qc(sql_q):
                                r, e = _comp_conn.execute_query(sql_q)
                                return r, e

                            # Helper for quoting
                            if _db_t == "MySQL":
                                def _q(c): return f"`{c}`"
                                def _qt(t): return f"`{t}`"
                            else:
                                def _q(c): return f'"{c}"'
                                def _qt(t): return f'"{t}"'

                            _schema_cols = table_schema.get("columns", [])
                            _col_names = [c["name"] for c in _schema_cols]
                            _col_list = ", ".join([_q(c) for c in _col_names])

                            analysis_summary = []

                            # 1. Row count
                            r, e = _qc(f"SELECT COUNT(*) as total_rows FROM {_qt(active_tbl)}")
                            total_rows = int(r.iloc[0, 0]) if (e is None and r is not None and len(r) > 0) else '?'
                            analysis_summary.append(f"📊 **Total rows**: {total_rows:,}" if isinstance(total_rows, int) else f"📊 **Total rows**: {total_rows}")

                            # 2. Exact duplicates (SQL-level)
                            try:
                                _pk_cols = set(table_schema.get("pk_columns", []))
                                if not _pk_cols:
                                    _pk_cols = {c for c in _col_names if c.lower() in ("id", "pk") or c.lower().endswith("_id") or c.lower().startswith("id_")}
                                _dup_cols = [c for c in _col_names if c not in _pk_cols]
                                if not _dup_cols:
                                    _dup_cols = _col_names
                                _dup_col_list = ", ".join([_q(c) for c in _dup_cols])

                                if _db_t == "MySQL":
                                    dup_sql = f"SELECT SUM(cnt-1) FROM (SELECT {_dup_col_list}, COUNT(*) as cnt FROM {_qt(active_tbl)} GROUP BY {_dup_col_list} HAVING COUNT(*) > 1) AS t"
                                else:
                                    dup_sql = f"SELECT SUM(cnt-1) FROM (SELECT {_dup_col_list}, COUNT(*) as cnt FROM {_qt(active_tbl)} GROUP BY {_dup_col_list} HAVING COUNT(*) > 1) AS t"
                                r, e = _qc(dup_sql)
                                dup_count = int(r.iloc[0, 0]) if (e is None and r is not None and len(r) > 0 and pd.notnull(r.iloc[0, 0])) else 0
                                analysis_summary.append(f"{'🔴' if dup_count > 0 else '✅'} **Exact duplicate rows**: {dup_count}")
                            except Exception:
                                analysis_summary.append("ℹ️ **Exact duplicates**: Could not compute")

                            # 3. Missing values per column
                            null_issues = []
                            for col_info in _schema_cols:
                                cn = col_info["name"]
                                r, e = _qc(f"SELECT COUNT(*) as null_count FROM {_qt(active_tbl)} WHERE {_q(cn)} IS NULL OR TRIM(CAST({_q(cn)} AS VARCHAR)) = ''" if _db_t != "MySQL" else f"SELECT COUNT(*) as null_count FROM {_qt(active_tbl)} WHERE {_q(cn)} IS NULL OR TRIM(CAST({_q(cn)} AS CHAR)) = ''")
                                if e is None and r is not None and len(r) > 0:
                                    nc = int(r.iloc[0, 0])
                                    if nc > 0:
                                        null_issues.append(f"{cn}: {nc} missing")
                            if null_issues:
                                analysis_summary.append(f"🔴 **Missing/null values**: {len(null_issues)} column(s) affected\n  → " + ", ".join(null_issues[:8]) + ("..." if len(null_issues) > 8 else ""))
                            else:
                                analysis_summary.append("✅ **Missing values**: None found")

                            # 4. Numeric outlier check (for numeric cols)
                            numeric_cols = [c["name"] for c in _schema_cols if any(t in c.get("type","").upper() for t in ["INT","FLOAT","DOUBLE","DECIMAL","NUMERIC","REAL","BIGINT","SMALLINT"])]
                            outlier_issues = []
                            for cn in numeric_cols[:5]:  # check first 5 numeric cols
                                try:
                                    r, e = _qc(f"SELECT AVG(CAST({_q(cn)} AS FLOAT)) as avg_val, STDDEV(CAST({_q(cn)} AS FLOAT)) as std_val FROM {_qt(active_tbl)} WHERE {_q(cn)} IS NOT NULL" if _db_t != "MySQL" else f"SELECT AVG({_q(cn)}) as avg_val, STD({_q(cn)}) as std_val FROM {_qt(active_tbl)} WHERE {_q(cn)} IS NOT NULL")
                                    if e is None and r is not None and len(r) > 0:
                                        avg_v = r.iloc[0, 0]
                                        std_v = r.iloc[0, 1]
                                        if avg_v is not None and std_v is not None and float(std_v) > 0:
                                            threshold = float(avg_v) + 3 * float(std_v)
                                            r2, e2 = _qc(f"SELECT COUNT(*) FROM {_qt(active_tbl)} WHERE {_q(cn)} > {threshold} OR {_q(cn)} < {float(avg_v) - 3 * float(std_v)}")
                                            if e2 is None and r2 is not None and len(r2) > 0 and int(r2.iloc[0, 0]) > 0:
                                                outlier_issues.append(f"{cn}: {int(r2.iloc[0, 0])} outliers (±3σ)")
                                except Exception:
                                    pass
                            if outlier_issues:
                                analysis_summary.append(f"🟡 **Numeric outliers** (3σ rule): " + ", ".join(outlier_issues))
                            elif numeric_cols:
                                analysis_summary.append(f"✅ **Numeric outliers**: None detected in checked columns")

                            # 5. Distinct value stats for categorical cols
                            str_cols = [c["name"] for c in _schema_cols if any(t in c.get("type","").upper() for t in ["VARCHAR","TEXT","CHAR","STRING","NVARCHAR"])]
                            low_cardinality = []
                            for cn in str_cols[:5]:
                                try:
                                    r, e = _qc(f"SELECT COUNT(DISTINCT {_q(cn)}) as uniq FROM {_qt(active_tbl)}")
                                    if e is None and r is not None and len(r) > 0:
                                        uniq = int(r.iloc[0, 0])
                                        if uniq == 1:
                                            low_cardinality.append(f"{cn} (only 1 unique value!)")
                                except Exception:
                                    pass
                            if low_cardinality:
                                analysis_summary.append(f"⚠️ **Low cardinality / constant columns**: " + ", ".join(low_cardinality))

                            # Format comprehensive report
                            report_text = f"## 🔍 Comprehensive Data Quality Report — `{active_tbl}`\n\n" + "\n\n".join(analysis_summary)
                            report_text += f"\n\n---\n💡 *Ask me about specific issues, e.g. 'Show duplicate rows' · 'Show rows where email is null' · 'Fix missing values'*"

                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": report_text,
                            "confidence": "High",
                        })
                        st.session_state.last_result = None
                        st.session_state.last_sql = ""
                        st.rerun()

                    else:
                        # ── Standard NL → SQL workflow ──
                        with st.spinner("🤖 Generating SQL..."):
                            sample_str = ""
                            if st.session_state.table_df is not None:
                                sample_str = st.session_state.table_df.head(5).to_string(index=False)

                            result = agent.generate_sql(
                                query_text,
                                table_schema,
                                db_type=db_type,
                                sample_data=sample_str,
                                all_tables_schemas=st.session_state.all_schemas,
                                active_table=active_tbl,
                            )

                        st.session_state.last_sql = result.get("sql", "")

                        if result.get("pending_confirmation"):
                            # Destructive — show modal, do NOT execute yet
                            result["user_query"] = query_text
                            st.session_state.pending_action = result
                            st.session_state.chat_messages.append({
                                "role": "assistant",
                                "content": f"⚠️ **Action requires your approval** — {result.get('explanation','')}",
                                "confidence": result.get("confidence","Medium"),
                            })
                            st.session_state.last_result = None
                            st.rerun()
                        else:
                            # READ — auto-execute immediately
                            with st.spinner("⚡ Executing..."):
                                exec_res = agent.execute_with_backup(
                                    conn, result["sql"], result,
                                    backup_dir=os.path.join(os.getcwd(), "exports"),
                                    user_query=query_text,
                                    table_schema=table_schema,
                                )
                            _handle_exec_result(exec_res, result)
                            st.rerun()


# ═══════════════════════════════════════════════════════════════
# TAB 5 — AI CLEANING STUDIO
# ═══════════════════════════════════════════════════════════════
with tab5:
    if not is_conn:
        st.info("🔌 Connect to a database first (Tab 1) to run AI cleaning.")
    else:
        conn = st.session_state.db_connector

        st.markdown('<div class="sec-hdr">🧹 <span>AI Cleaning Studio</span>'
                    '<span class="sec-badge">FULL 12-PHASE PIPELINE</span></div>', unsafe_allow_html=True)

        # Table selector
        if st.session_state.db_tables:
            clean_tbl = st.selectbox("Select table to clean:",
                st.session_state.db_tables,
                index=st.session_state.db_tables.index(st.session_state.active_table)
                      if st.session_state.active_table in st.session_state.db_tables else 0,
                key="clean_tbl_sel")
        else:
            st.warning("No tables found.")
            clean_tbl = None

        if clean_tbl:
            # Load preview
            try:
                preview_df = conn.load_table(clean_tbl, limit=5000)
            except Exception as e:
                st.error(f"Failed to load table: {e}")
                preview_df = None

            if preview_df is not None:
                # Pre-cleaning profile
                st.markdown('<div class="sec-hdr">📊 <span>Pre-Cleaning Profile</span></div>', unsafe_allow_html=True)
                null_counts = preview_df.isna().sum()
                total_nulls = int(null_counts.sum())
                # Exact duplicate detection (exclude PKs + normalize)
                try:
                    _pk_cols = set(st.session_state.table_schema.get("pk_columns", [])) if hasattr(st.session_state, "table_schema") and st.session_state.table_schema else set()
                    if not _pk_cols:
                        _pk_cols = {c for c in preview_df.columns if c.lower() in ("id", "pk") or c.lower().endswith("_id") or c.lower().startswith("id_")}
                    _dup_cols = [c for c in preview_df.columns if c not in _pk_cols]
                    _dup_cols = _dup_cols if _dup_cols else list(preview_df.columns)
                    
                    # Normalize missing values for pandas comparison
                    def _norm_val(v):
                        s = str(v).strip().lower()
                        return "__NULL__" if s in {"none", "nan", "nat", "null", "", "na", "n/a"} else s
                    
                    _norm_df = preview_df[_dup_cols].applymap(_norm_val)
                    dup_count = int(_norm_df.duplicated().sum())
                except Exception:
                    dup_count = int(preview_df.duplicated().sum())
                    
                null_pct    = round(total_nulls / max(len(preview_df) * len(preview_df.columns), 1) * 100, 1)

                p1, p2, p3, p4 = st.columns(4)
                with p1:
                    st.markdown(f'<div class="mini-m"><div class="mv" style="color:#e2e8f0">{len(preview_df)}</div><div class="ml">Rows</div></div>', unsafe_allow_html=True)
                with p2:
                    st.markdown(f'<div class="mini-m"><div class="mv" style="color:#e2e8f0">{len(preview_df.columns)}</div><div class="ml">Columns</div></div>', unsafe_allow_html=True)
                with p3:
                    nc = "#f87171" if total_nulls > 0 else "#4ade80"
                    st.markdown(f'<div class="mini-m"><div class="mv" style="color:{nc}">{total_nulls}</div><div class="ml">Nulls ({null_pct}%)</div></div>', unsafe_allow_html=True)
                with p4:
                    dc = "#f87171" if dup_count > 0 else "#4ade80"
                    st.markdown(f'<div class="mini-m"><div class="mv" style="color:{dc}">{dup_count}</div><div class="ml">Duplicates</div></div>', unsafe_allow_html=True)

                # Null heatmap by column
                if total_nulls > 0:
                    with st.expander("📊 Null Analysis by Column"):
                        null_df = null_counts[null_counts > 0].reset_index()
                        null_df.columns = ["Column", "Null Count"]
                        null_df["Null %"] = (null_df["Null Count"] / len(preview_df) * 100).round(1)
                        st.dataframe(null_df, use_container_width=True, hide_index=True)

                # Cleaning options
                st.markdown('<div class="sec-hdr">⚙️ <span>Cleaning Options</span></div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    write_back = st.checkbox("Write cleaned data back to database", value=True)
                    create_backup_opt = st.checkbox("Create backup before cleaning", value=True)
                with c2:
                    export_csv = st.checkbox("Export cleaned CSV locally", value=True)

                if st.button("🚀 Run AI Cleaning Pipeline", type="primary", use_container_width=True):

                    with st.spinner("🧹 Running 12-phase cleaning pipeline..."):
                        log_msgs = []
                        log_ph   = st.empty()

                        def _log(msg):
                            log_msgs.append(msg)
                            display_logs = []
                            for line in log_msgs[-40:]:
                                if "Error" in line or "Failed" in line or "❌" in line:
                                    display_logs.append(f'<span style="color:#f87171">{line}</span>')
                                elif "Phase" in line and ":" in line:
                                    display_logs.append(f'<span style="color:#a78bfa;font-weight:600">{line}</span>')
                                elif "Completed" in line or "✅" in line or "Done" in line:
                                    display_logs.append(f'<span style="color:#4ade80">{line}</span>')
                                elif "[Pass" in line or "[Dedup" in line or "[Domain" in line or "[Rule" in line:
                                    display_logs.append(f'<span style="color:#22d3ee">{line}</span>')
                                else:
                                    display_logs.append(line)
                            log_ph.markdown(
                                '<div class="log-container" style="background:#0f172a; border-radius:12px; padding:1.2rem; font-family:\'Courier New\', monospace; font-size:0.85rem; color:#e2e8f0; height:350px; overflow-y:auto; border:1px solid #1e293b; box-shadow:inset 0 2px 10px rgba(0,0,0,0.2); white-space: pre-wrap; line-height: 1.6;">' + "\n".join(display_logs) + '</div>',
                                unsafe_allow_html=True
                            )

                        # Backup first
                        if create_backup_opt:
                            _log("Creating table backups before cleaning...")
                            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            ok, bname = conn.create_backup(clean_tbl, ts)
                            if ok:
                                _log(f"  ✅ DB Clone: Created table '{bname}' in database.")
                                csv_dir = os.path.join(os.getcwd(), "exports")
                                ok2, csv_p = conn.create_backup_csv(clean_tbl, csv_dir)
                                if ok2:
                                    _log(f"  ✅ Local CSV: Saved to {csv_p}")
                            else:
                                _log(f"  ⚠️ Backup failed: {bname}")

                        # Load full table for cleaning
                        _log(f"Loading table '{clean_tbl}'...")
                        try:
                            full_df = conn.load_table(clean_tbl)
                            _log(f"  Loaded {len(full_df)} rows, {len(full_df.columns)} columns")
                        except Exception as e:
                            _log(f"  ❌ Load failed: {e}")
                            full_df = preview_df

                        # Run pipeline
                        from backend.pipeline import PipelineOrchestrator
                        orch = PipelineOrchestrator(df=full_df, log_callback=_log)
                        try:
                            clean_df, meta = orch.execute()
                        except Exception as e:
                            _log(f"  ❌ Pipeline error: {e}")
                            import traceback
                            _log(traceback.format_exc())
                            clean_df = full_df
                            meta = {}

                        # Results
                        st.session_state.cleaning_result = {"df": clean_df, "meta": meta, "table": clean_tbl, "logs": log_msgs}
                        StateManager.save_pipeline_state(clean_df, meta, clean_tbl, log_msgs)

                    # Write-back
                    if write_back:
                        with st.spinner("Writing cleaned data back to database..."):
                            ok, msg = conn.write_dataframe(clean_df, clean_tbl, if_exists="replace")
                        if ok:
                            st.success(f"✅ {msg}")
                        else:
                            st.error(f"❌ Write-back failed: {msg}")

                    # Export CSV
                    if export_csv:
                        os.makedirs("exports", exist_ok=True)
                        ts      = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        fp      = os.path.join("exports", f"{clean_tbl}_cleaned_{ts}.csv")
                        clean_df.to_csv(fp, index=False)
                        st.info(f"📥 Exported: `{fp}`")

                # Previous cleaning result
                if st.session_state.cleaning_result and st.session_state.cleaning_result.get("table") == clean_tbl:
                    cr = st.session_state.cleaning_result
                    try:
                        from components.ui_components import render_cleaning_results
                        render_cleaning_results(st, cr["df"], cr["meta"], cr.get("logs", []))
                    except:
                        pass
                    
                    st.download_button(
                        "📥 Download Cleaned Data",
                        data=cr["df"].to_csv(index=False).encode("utf-8"),
                        file_name=f"{clean_tbl}_cleaned.csv",
                        mime="text/csv",
                    )


# ═══════════════════════════════════════════════════════════════
# TAB 6 — AUDIT LOG
# ═══════════════════════════════════════════════════════════════
with tab6:
    st.markdown('<div class="sec-hdr">📋 <span>Audit Log</span>'
                f'<span class="sec-badge">{len(st.session_state.audit_log)} ENTRIES</span></div>',
                unsafe_allow_html=True)

    log = st.session_state.audit_log

    if not log:
        st.info("No queries have been executed yet. The audit log will appear here as you use the AI Query Studio.")
    else:
        # Summary stats
        total     = len(log)
        succeeded = sum(1 for e in log if e.get("success"))
        backups   = sum(len(e.get("backups",[])) for e in log)
        al1, al2, al3 = st.columns(3)
        with al1:
            st.markdown(f'<div class="mini-m"><div class="mv" style="color:#e2e8f0">{total}</div><div class="ml">Total Queries</div></div>', unsafe_allow_html=True)
        with al2:
            sc = "#4ade80" if succeeded == total else "#fbbf24"
            st.markdown(f'<div class="mini-m"><div class="mv" style="color:{sc}">{succeeded}</div><div class="ml">Succeeded</div></div>', unsafe_allow_html=True)
        with al3:
            st.markdown(f'<div class="mini-m"><div class="mv" style="color:#fbbf24">{backups}</div><div class="ml">Backups Created</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        for entry in reversed(log):
            ok_icon = "✅" if entry.get("success") else "❌"
            bg      = "rgba(74,222,128,0.04)" if entry.get("success") else "rgba(248,113,113,0.04)"
            bc      = "rgba(74,222,128,0.25)" if entry.get("success") else "rgba(248,113,113,0.25)"
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {bc};border-radius:10px;
                        padding:0.7rem 1rem;margin-bottom:0.4rem;font-size:0.83rem">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span>{ok_icon} <b style="color:#e2e8f0">{entry.get('table','?')}</b>
                  — {entry.get('query','')}</span>
                <span style="color:#475569;font-size:0.72rem">{entry.get('timestamp','')}</span>
              </div>
              {" ".join(['<span class="bkp">Backup: ' + str(b.get("backup_table","?")) + '</span>' for b in entry.get('backups',[])])}
            </div>
            """, unsafe_allow_html=True)
            with st.expander(f"👁 View SQL — {entry.get('timestamp','')}"):
                st.code(entry.get("sql",""), language="sql")

        # Export audit log
        if st.button("📥 Export Audit Log as JSON"):
            export_log = [{k: v for k, v in e.items() if k != "result_df"} for e in log]
            st.download_button(
                "Download audit_log.json",
                data=json.dumps(export_log, indent=2, default=str).encode(),
                file_name="audit_log.json",
                mime="application/json",
            )
        if st.button("🗑️ Clear Audit Log"):
            st.session_state.audit_log = []
            st.rerun()

# Render floating system monitor
from components.system_monitor import render_system_monitor
render_system_monitor()
