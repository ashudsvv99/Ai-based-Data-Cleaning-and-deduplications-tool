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
            st.session_state.relationships = agent.discover_relationships(schemas) if hasattr(agent, 'discover_relationships') else []
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
    if exec_res.get("success"):
        rdf   = exec_res.get("result_df")
        nrows = len(rdf) if rdf is not None else exec_res.get("rows_affected", 0)
        msg   = query_meta.get("explanation", "Query executed successfully.")
        if rdf is None:
            msg += f"\n✅ {nrows} rows affected."
        st.session_state.last_result = exec_res
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": msg,
            "confidence": query_meta.get("confidence", "Medium"),
        })
        # Backups info
        for bk in exec_res.get("backups", []):
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": f"🔒 Backup created: `{bk.get('backup_table','?')}` · CSV: `{bk.get('csv_path','?')}`",
                "confidence": "High",
            })
        # Follow-up suggestions
        if rdf is not None:
            summary = f"{nrows} rows" if nrows > 0 else "No results"
            try:
                chips = st.session_state.nl_agent.suggest_followup_queries(
                    query_meta.get("user_query", ""),
                    summary,
                    query_meta.get("affected_tables", [st.session_state.active_table])[0]
                    if query_meta.get("affected_tables") else (st.session_state.active_table or ""),
                )
                st.session_state.followup_chips = chips
            except Exception:
                st.session_state.followup_chips = []
    else:
        err = exec_res.get("error", "Unknown error")
        st.session_state.last_result = exec_res
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": f"❌ Execution failed: {err}",
            "confidence": "Low",
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
    "📊 Health Profiler",
    "💬 AI Query Studio",
    "🧹 AI Cleaning",
    "📋 Audit Log",
])

# ═══════════════════════════════════════════════════════════════
# TAB 1 — CONNECT
# ═══════════════════════════════════════════════════════════════
with tab1:
    if is_conn:
        c = st.session_state.db_connector.get_connection_summary()
        st.markdown(f"""
        <div class="gpanel ok anim" style="padding:1.5rem;display:flex;justify-content:space-between;align-items:center">
          <div>
            <div style="font-weight:800;color:#4ade80;font-size:1.4rem">✅ Connected to {c['db_type']}</div>
            <div style="color:#94a3b8;margin-top:4px">{c.get('host','') or ''} · DB: <b>{c['database']}</b></div>
          </div>
          <div style="text-align:right">
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
                for k in ["db_connector","db_tables","all_schemas","active_table","table_schema","table_df","relationships","db_overview"]:
                    st.session_state[k] = [] if isinstance(st.session_state.get(k), list) else None
                st.rerun()
    else:
        # ── DB type selector ──
        st.markdown('<div class="sec-hdr">🔌 <span>Select Database</span></div>', unsafe_allow_html=True)
        db_names = list(DB_TYPES.keys())
        for row_start in range(0, len(db_names), 3):
            row_dbs = db_names[row_start:row_start+3]
            cols = st.columns(len(row_dbs))
            for i, db_name in enumerate(row_dbs):
                meta = DB_TYPES[db_name]
                is_sel = st.session_state.db_type_sel == db_name
                cls = "db-card selected" if is_sel else "db-card"
                with cols[i]:
                    st.markdown(f"""
                    <div class="{cls}">
                      <div class="db-icon">{meta['icon']}</div>
                      <div class="db-name">{db_name}</div>
                      <div class="db-desc">{meta['description']}</div>
                      {"<div style='font-size:0.65rem;color:#334155'>Port "+str(meta['default_port'])+"</div>" if meta['default_port'] else ""}
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("Select", key=f"sel_{db_name}", use_container_width=True):
                        st.session_state.db_type_sel = db_name
                        st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Connection form ──
        db_type = st.session_state.db_type_sel
        meta    = DB_TYPES[db_type]
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
                            st.session_state.db_params.get("ssl_mode", "disable")))
                if db_type == "SQL Server":
                    params["odbc_driver"] = st.text_input("ODBC Driver",
                        value=st.session_state.db_params.get("odbc_driver", "ODBC Driver 17 for SQL Server"))

            with st.expander("⚙️ Advanced Options"):
                params["pool_size"] = st.number_input("Connection Pool Size", 1, 20, 5)
                params["timeout"]   = st.number_input("Query Timeout (s)", 5, 600, 30)
                params["read_only"] = st.checkbox("Read-Only Mode (no write-back)", value=False)

            c_test, c_save = st.columns(2)
            with c_test:
                test_btn = st.form_submit_button("⚡ Test Connection", use_container_width=True)
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
        schemas   = st.session_state.all_schemas
        rels      = st.session_state.relationships

        st.markdown('<div class="sec-hdr">🗺️ <span>Database Overview</span>'
                    f'<span class="sec-badge">{len(schemas)} TABLES · {len(rels)} RELATIONSHIPS</span></div>',
                    unsafe_allow_html=True)

        # ── Relationship graph removed as requested ──────────────────────
        # ── Relationship list ────────────────────────────────────
        if rels:
            st.markdown('<div class="sec-hdr">🔗 <span>Relationships Dictionary</span></div>', unsafe_allow_html=True)
            
            # Format relationships for a structured view
            rel_data = []
            for rel in rels:
                rel_data.append({
                    "Type": "🔑 Foreign Key" if rel["type"] == "FK" else "🔍 Inferred",
                    "Source Table": rel["from_table"],
                    "Source Column": rel["from_col"],
                    "Target Table": rel["to_table"],
                    "Target Column": rel["to_col"]
                })
            
            st.dataframe(
                pd.DataFrame(rel_data),
                use_container_width=True,
                hide_index=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)
        elif schemas:
            st.info("No FK relationships detected. Naming heuristics found no matching columns.")

        # ── Table summary cards ──────────────────────────────────
        st.markdown('<div class="sec-hdr">📋 <span>Table Summaries</span></div>', unsafe_allow_html=True)
        conn = st.session_state.db_connector
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
                st.markdown(f'<div class="mini-m"><div class="mv" style="color:#22d3ee">{tdf.duplicated().sum()}</div><div class="ml">Exact Dupes</div></div>', unsafe_allow_html=True)
            st.dataframe(tdf.head(100), use_container_width=True, height=300)


# ═══════════════════════════════════════════════════════════════
# TAB 3 — HEALTH PROFILER
# ═══════════════════════════════════════════════════════════════
with tab3:
    if not is_conn:
        st.info("🔌 Connect to a database first (Tab 1) to run the health profiler.")
    else:
        st.markdown('<div class="sec-hdr">📊 <span>Health Profiler</span></div>', unsafe_allow_html=True)
        
        if st.session_state.db_tables:
            hp_tbl = st.selectbox("Select table to profile:",
                st.session_state.db_tables,
                index=st.session_state.db_tables.index(st.session_state.active_table)
                      if st.session_state.active_table in st.session_state.db_tables else 0,
                key="hp_tbl_sel")
        else:
            st.warning("No tables found.")
            hp_tbl = None

        if hp_tbl:
            tbl = hp_tbl
            connector = st.session_state.db_connector
            
            st.markdown("Run a comprehensive scan to detect missing values, exact duplicates, and fuzzy inconsistencies.")
            
            if st.button("🚀 Run Complete Health Check", key="run_health_check", type="primary"):
                with st.spinner("Profiling dataset... (loading up to 10,000 rows for fuzzy logic)"):
                    from backend.profiler import DatasetProfiler
                    
                    try:
                        # Load max 10k rows for performance
                        df_sample = connector.load_table(tbl, limit=10000)
                        
                        if df_sample.empty:
                            st.warning("Table is empty.")
                        else:
                            # 1. Base Profiling
                            profiler = DatasetProfiler(df_sample)
                            profile_stats = profiler.profile()
                            
                            st.markdown("#### 📈 Overview Stats (10k sample)")
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("Total Rows", profile_stats["total_rows"])
                            c2.metric("Total Columns", profile_stats["total_columns"])
                            c3.metric("Data Quality Score", f"{profile_stats['quality_score']}/100")
                            c4.metric("Exact Duplicates", profile_stats["exact_duplicate_rows"])
                            
                            st.markdown("#### 🧩 Missing Values per Column")
                            m_df = pd.DataFrame([
                                {"Column": col, "Missing": stats["null_count"], "Missing %": stats["null_percentage"]}
                                for col, stats in profile_stats["column_statistics"].items()
                                if stats["null_count"] > 0
                            ])
                            if not m_df.empty:
                                st.dataframe(m_df, use_container_width=True)
                            else:
                                st.success("✅ No missing values found in the sampled data!")
                                
                            # Show Exact Duplicates
                            st.markdown("#### 👯 Exact Duplicates")
                            if profile_stats["exact_duplicate_rows"] > 0:
                                st.warning(f"⚠️ Found {profile_stats['exact_duplicate_rows']} exact duplicate rows!")
                                exact_dupes_df = df_sample[df_sample.duplicated(keep=False)].sort_values(list(df_sample.columns))
                                st.dataframe(exact_dupes_df, use_container_width=True)
                            else:
                                st.success("✅ No exact duplicates found!")
                            
                            # 2. Fuzzy Deduplication
                            st.markdown("#### 👥 Fuzzy Deduplication (Near-Matches)")
                            from backend.schema_detector import classify_all_columns
                            from cleaning.deduplication import DeduplicationEngine
                            
                            # Auto-detect schema to get baseline strategies for dedup
                            schema_mapping = classify_all_columns(df_sample)
                            
                            dedup_strats = {}
                            id_cols_to_drop = []
                            for col, info in schema_mapping.items():
                                stype = info.get("semantic_type", "")
                                if stype == "ID_Code":
                                    id_cols_to_drop.append(col)
                                    dedup_strats[col] = "none"
                                elif stype in ("Name", "Free_Text"):
                                    dedup_strats[col] = "fuzzy_name"
                                elif stype in ("Location", "Categorical"):
                                    dedup_strats[col] = "blocking_key"
                                else:
                                    dedup_strats[col] = "none"

                            # Fallback: if no text column was found for fuzzy matching, promote a categorical
                            if "fuzzy_name" not in dedup_strats.values():
                                for col, strat in dedup_strats.items():
                                    if strat == "blocking_key":
                                        dedup_strats[col] = "fuzzy_name"
                                        break
                                    
                            # Drop IDs from sample so Pass 1 doesn't aggressively merge valid transactions
                            df_eval = df_sample.drop(columns=id_cols_to_drop)

                            # Run engine in Predictive intent to prevent business rules from aggressively merging IDs
                            dedup = DeduplicationEngine(df_eval, dedup_strats, dataset_intent="Predictive")
                            dedup.execute() # Executes and populates dedup.cluster_report
                            
                            clusters = dedup.cluster_report
                            changes = dedup.dedup_changes
                            if clusters and changes:
                                fuzzy_count = sum(c["cluster_size"] for c in clusters)
                                st.warning(f"⚠️ Found {fuzzy_count} records in {len(clusters)} fuzzy clusters!")
                                st.markdown("**Detected Fuzzy Duplicated Values:**")
                                
                                comp_df = pd.DataFrame(changes)
                                # Convert dicts/lists to strings to prevent 'unhashable type: dict' during drop_duplicates
                                for c in comp_df.columns:
                                    comp_df[c] = comp_df[c].apply(lambda x: str(x) if isinstance(x, (dict, list)) else x)
                                comp_df = comp_df.drop_duplicates().reset_index(drop=True)
                                st.dataframe(comp_df, use_container_width=True)
                            elif clusters:
                                fuzzy_count = sum(c["cluster_size"] for c in clusters)
                                st.warning(f"⚠️ Found {fuzzy_count} records in {len(clusters)} fuzzy clusters, but no text differences detected (likely exact matches).")
                            else:
                                st.success("✅ No fuzzy duplicates detected!")
                                
                    except Exception as e:
                        st.error(f"Error during profiling: {e}")


# ═══════════════════════════════════════════════════════════════
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

            # Quick suggestions
            if st.session_state.suggest_queries:
                st.markdown('<div class="sec-hdr">⚡ <span>Quick Queries</span></div>', unsafe_allow_html=True)
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
                chat_html = '<div class="chat-container" id="chat-box">'
                if not st.session_state.chat_messages:
                    chat_html += (
                        '<div style="text-align:center;color:#475569;padding:2rem;font-size:0.85rem">'
                        '💬 Ask anything in plain English about your data.<br>'
                        '<span style="font-size:0.75rem">e.g. "Show me the top 10 customers" · '
                        '"Find duplicate emails" · "How many nulls in each column?"</span>'
                        '</div>'
                    )
                for msg in st.session_state.chat_messages:
                    if msg["role"] == "user":
                        chat_html += f'<div class="chat-bubble-user">{msg["content"]}</div>'
                    else:
                        conf = msg.get("confidence", "Medium")
                        conf_cls = "chat-conf-high" if conf=="High" else "chat-conf-med" if conf=="Medium" else "chat-conf-low"
                        chat_html += (
                            f'<div class="chat-bubble-ai">'
                            f'<div>{msg["content"]}</div>'
                            f'<div class="chat-meta"><span class="{conf_cls}">● {conf}</span></div>'
                            f'</div>'
                        )
                chat_html += '</div>'
                st.markdown(chat_html, unsafe_allow_html=True)

                # ── Query result display ─────────────────────────
                last_result = st.session_state.get("last_result")
                if last_result:
                    rdf = last_result.get("result_df")
                    if rdf is not None and len(rdf) > 0:
                        st.markdown(f'<div style="font-size:0.75rem;color:#64748b;margin-bottom:4px">'
                                    f'✓ {len(rdf)} rows returned · {last_result.get("execution_time",0):.2f}s</div>',
                                    unsafe_allow_html=True)
                        st.dataframe(rdf, use_container_width=True, height=min(350, 35*len(rdf)+40))
                    if last_result.get("error"):
                        st.error(f"❌ {last_result['error']}")

                # ── SQL toggle ───────────────────────────────────
                if st.session_state.get("last_sql"):
                    with st.expander("👁 View Generated SQL"):
                        st.code(st.session_state.last_sql, language="sql")

                # ── Follow-up chips ──────────────────────────────
                if st.session_state.followup_chips:
                    st.markdown("**Follow-up suggestions:**")
                    chip_cols = st.columns(len(st.session_state.followup_chips))
                    for i, chip in enumerate(st.session_state.followup_chips):
                        with chip_cols[i]:
                            if st.button(f"💡 {chip[:40]}", key=f"chip_{i}", use_container_width=True):
                                st.session_state._run_query_nl = chip
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
                        placeholder="e.g. Show top 5 customers by order count · Find duplicate emails · Delete rows with no name",
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
                dup_count   = int(preview_df.duplicated().sum())
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
                    from ui_components import render_cleaning_results
                    render_cleaning_results(st, cr["df"], cr["meta"], cr.get("logs", []))
                    
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
