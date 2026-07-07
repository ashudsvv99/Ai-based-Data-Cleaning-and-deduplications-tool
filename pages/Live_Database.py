"""
pages/Live_Database.py  — Universal Database Connector & NL Query Console

Features:
  - DB type selector with visual cards (PostgreSQL, MySQL, SQLite, SQL Server, Oracle, IBM DB2)
  - Connection form with host / port / database / username / password / SSL / pool settings
  - Live connection test indicator
  - Table browser with schema explorer, row-count, preview
  - AI Cleaning Pipeline: run the full 12-phase pipeline on any live table
  - NL Query Console: type in plain English → LLM generates SQL → confirms destructive ops → executes
  - Automatic backup (table-copy + CSV) before any destructive action
  - Query history / audit log panel
"""
import os
import json
import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IntelliClean · DB Connector",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# CSS — same dark-glassmorphism theme as main app
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #0b0d17; color: #e2e8f0; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1500px; }

/* DB type cards */
.db-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px; padding: 1.2rem 1.4rem;
    cursor: pointer; transition: all 0.2s;
    display: flex; flex-direction: column; gap: 6px;
}
.db-card:hover { border-color: rgba(139,92,246,0.5); background: rgba(139,92,246,0.06); transform: translateY(-2px); }
.db-card.selected { border-color: #a78bfa; background: rgba(139,92,246,0.12); box-shadow: 0 0 20px rgba(139,92,246,0.2); }
.db-icon { font-size: 1.8rem; }
.db-name { font-size: 0.92rem; font-weight: 700; color: #e2e8f0; }
.db-desc { font-size: 0.72rem; color: #64748b; }
.db-port { font-size: 0.68rem; color: #475569; }

/* Connected badge */
.conn-badge-ok  { display:inline-flex;align-items:center;gap:5px;background:rgba(74,222,128,0.1);border:1px solid rgba(74,222,128,0.3);border-radius:20px;padding:3px 12px;font-size:0.75rem;font-weight:600;color:#4ade80; }
.conn-badge-err { display:inline-flex;align-items:center;gap:5px;background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);border-radius:20px;padding:3px 12px;font-size:0.75rem;font-weight:600;color:#f87171; }

/* Section headers */
.section-header {
    display:flex;align-items:center;gap:10px;
    font-size:1rem;font-weight:700;color:#e2e8f0;
    border-bottom:1px solid rgba(255,255,255,0.07);
    padding-bottom:0.6rem;margin:1.8rem 0 1rem;
}
.section-badge {
    background:rgba(139,92,246,0.15);border:1px solid rgba(139,92,246,0.3);
    border-radius:6px;padding:2px 8px;font-size:0.7rem;font-weight:700;color:#a78bfa;
}

/* Glass panel */
.glass-panel {
    background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);
    border-radius:14px;padding:1.4rem 1.6rem;margin-bottom:1rem;
}
.glass-panel.success { border-color:rgba(74,222,128,0.25);background:rgba(74,222,128,0.04); }
.glass-panel.warning { border-color:rgba(251,191,36,0.25);background:rgba(251,191,36,0.04); }
.glass-panel.error   { border-color:rgba(248,113,113,0.25);background:rgba(248,113,113,0.04); }
.glass-panel.info    { border-color:rgba(34,211,238,0.25);background:rgba(34,211,238,0.04); }

/* Table card */
.table-card {
    background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);
    border-radius:10px;padding:0.8rem 1.1rem;margin-bottom:0.5rem;
    cursor:pointer;transition:border-color 0.15s;
    display:flex;align-items:center;justify-content:space-between;
}
.table-card:hover { border-color:rgba(139,92,246,0.4); }
.table-card.active { border-color:#a78bfa;background:rgba(139,92,246,0.08); }

/* NL Query box */
.query-console {
    background:rgba(6,8,16,0.95);border:1px solid rgba(139,92,246,0.25);
    border-radius:14px;padding:1.2rem 1.4rem;margin:1rem 0;
}
.sql-preview {
    background:#060810;border:1px solid rgba(255,255,255,0.07);
    border-left:3px solid #a78bfa;border-radius:10px;
    padding:1rem 1.2rem;font-family:'Courier New',monospace;
    font-size:0.82rem;color:#a5f3fc;white-space:pre-wrap;
    overflow-x:auto;margin:0.5rem 0;
}

/* Backup badge */
.backup-badge {
    display:inline-flex;align-items:center;gap:5px;
    background:rgba(251,191,36,0.1);border:1px solid rgba(251,191,36,0.3);
    border-radius:8px;padding:4px 10px;font-size:0.75rem;font-weight:600;color:#fbbf24;
    margin:2px;
}

/* Query history item */
.hist-item {
    background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);
    border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.4rem;font-size:0.82rem;
}

/* Stagger animation */
@keyframes fadeInUp { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }
.anim-in { animation: fadeInUp 0.3s ease forwards; }

/* Suggestion chip */
.suggest-chip {
    display:inline-flex;align-items:center;gap:5px;
    background:rgba(34,211,238,0.08);border:1px solid rgba(34,211,238,0.2);
    border-radius:20px;padding:4px 12px;font-size:0.74rem;font-weight:500;color:#22d3ee;
    cursor:pointer;margin:3px;white-space:nowrap;transition:background 0.15s;
}
.suggest-chip:hover { background:rgba(34,211,238,0.16); }

/* Primary btn */
.stButton > button[kind="primary"] {
    background:linear-gradient(135deg,#7c3aed 0%,#9333ea 100%) !important;
    border:none !important;border-radius:12px !important;font-weight:700 !important;
    color:white !important;box-shadow:0 4px 24px rgba(124,58,237,0.4) !important;
}
/* Sidebar */
[data-testid="stSidebar"] { background:#0d1117 !important; border-right:1px solid rgba(255,255,255,0.06) !important; }
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255, 255, 255, 0.02) !important;
    border-radius: 12px !important;
    padding: 6px !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    gap: 8px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    padding: 10px 20px !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    border: none !important;
    background: transparent !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #e2e8f0 !important;
    background: rgba(255, 255, 255, 0.05) !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.2) 0%, rgba(139, 92, 246, 0.35) 100%) !important;
    color: #c4b5fd !important;
    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.15) !important;
}
[data-testid="stDataFrame"] { border-radius:12px;overflow:hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Imports (deferred to avoid slowing the page on first load)
# ─────────────────────────────────────────────────────────────
from backend.db_connector import DatabaseConnector, DB_TYPES
from agents.nl_query_agent import NLQueryAgent
from agents.llm_client import LMStudioClient

# ─────────────────────────────────────────────────────────────
# Session state init
# ─────────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "db_connector":    None,
        "db_type_sel":     "PostgreSQL",
        "db_params":       {},
        "db_tables":       [],
        "active_table":    None,
        "table_schema":    {},
        "table_df":        None,
        "nl_query_result": None,
        "pending_sql":     None,
        "query_history":   [],
        "suggest_queries": [],
        "nl_agent":        None,
        "cleaning_result": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ─────────────────────────────────────────────────────────────
# Sidebar — LLM config + breadcrumb
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0 0.5rem;text-align:center">
      <div style="font-size:2rem">✦</div>
      <div style="font-size:1rem;font-weight:700;color:#a78bfa">IntelliClean AI</div>
      <div style="font-size:0.72rem;color:#475569;margin-top:2px">DB Connector · v2.0</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### ⚙️ LLM Configuration")
    lm_url = st.text_input("LM Studio URL", value="http://localhost:1234/v1")
    os.environ["LM_STUDIO_URL"] = lm_url
    st.markdown("---")
    st.markdown("### 🗄️ Navigation")
    st.page_link("app.py", label="← File Upload (CSV/Excel)", icon="📂")
    st.markdown("---")

    # Show active connection summary
    if st.session_state.db_connector and st.session_state.db_connector.is_connected:
        c = st.session_state.db_connector.get_connection_summary()
        st.markdown(f"""
        <div class="glass-panel success" style="font-size:0.8rem;padding:0.8rem 1rem">
          <div style="font-weight:700;color:#4ade80;margin-bottom:4px">● Connected</div>
          <div style="color:#94a3b8">{c['db_type']} · {c['host'] or c['database']}</div>
          <div style="color:#64748b;font-size:0.72rem">DB: {c['database']}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔌 Disconnect", use_container_width=True):
            st.session_state.db_connector.disconnect()
            st.session_state.db_connector = None
            st.session_state.db_tables = []
            st.session_state.active_table = None
            st.rerun()

# ─────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#1e1b4b 0%,#0f172a 50%,#0d1a2d 100%);
     border:1px solid rgba(139,92,246,0.3);border-radius:20px;padding:2.5rem 3rem;
     margin-bottom:2rem;position:relative;overflow:hidden">
  <div style="font-size:0.75rem;font-weight:600;color:#a78bfa;letter-spacing:0.05em;
       margin-bottom:0.7rem">🗄️ UNIVERSAL DATABASE CONNECTOR</div>
  <div style="font-size:2.2rem;font-weight:800;
       background:linear-gradient(135deg,#e2e8f0 30%,#a78bfa 100%);
       -webkit-background-clip:text;-webkit-text-fill-color:transparent">
    Live Database Cleaning & Query Studio</div>
  <div style="font-size:0.95rem;color:#94a3b8;margin-top:0.5rem;max-width:650px">
    Connect to any SQL database, run AI-powered cleaning on live tables,
    and query data using plain English — the LLM generates and executes SQL safely.
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Main layout: left panel (connector) + right panel (studio)
# ─────────────────────────────────────────────────────────────
is_conn = bool(st.session_state.db_connector and st.session_state.db_connector.is_connected)

if is_conn:
    c = st.session_state.db_connector.get_connection_summary()
    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown(f'''
        <div class="glass-panel success" style="font-size:1.1rem;padding:1.5rem;display:flex;justify-content:space-between;align-items:center;border-left:4px solid #4ade80">
          <div>
            <div style="font-weight:800;color:#4ade80;margin-bottom:4px;font-size:1.4rem">✅ Connected to {c['db_type']}</div>
            <div style="color:#94a3b8;font-size:1rem">{c['host'] or c['database']}</div>
          </div>
          <div style="text-align:right">
            <div style="color:#64748b;font-size:0.9rem;text-transform:uppercase;letter-spacing:1px">Database</div>
            <div style="color:#e2e8f0;font-weight:600;font-size:1.1rem">{c['database']}</div>
          </div>
        </div>
        ''', unsafe_allow_html=True)
    with c2:
        st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)
        if st.button("🔌 Disconnect Server", type="primary", use_container_width=True, key="btn_disconnect_top"):
            st.session_state.db_connector.disconnect()
            st.session_state.db_connector = None
            st.session_state.db_tables = []
            st.session_state.active_table = None
            st.rerun()
            
    st.markdown("<br>", unsafe_allow_html=True)
    col_left = st.empty()
    col_right = st.container()
else:
    col_left, col_right = st.columns([2, 3], gap="large")

# ════════════════════════════════════════════════════════════════
# LEFT PANEL — Connection setup
# ════════════════════════════════════════════════════════════════
with col_left:
    if not is_conn:
        st.markdown('<div class="section-header">🔌 <span>Select Database Type</span></div>', unsafe_allow_html=True)

        # DB type cards — 2 per row
        db_names = list(DB_TYPES.keys())
        for row_start in range(0, len(db_names), 3):
            row_dbs = db_names[row_start: row_start + 3]
            cols = st.columns(len(row_dbs))
            for i, db_name in enumerate(row_dbs):
                meta = DB_TYPES[db_name]
                is_sel = st.session_state.db_type_sel == db_name
                card_class = "db-card selected" if is_sel else "db-card"
                with cols[i]:
                    st.markdown(f"""
                    <div class="{card_class}">
                      <div class="db-icon">{meta['icon']}</div>
                      <div class="db-name">{db_name}</div>
                      <div class="db-desc">{meta['description']}</div>
                      {"<div class='db-port'>Port: " + str(meta['default_port']) + "</div>" if meta['default_port'] else ""}
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Select", key=f"sel_{db_name}", use_container_width=True):
                        st.session_state.db_type_sel = db_name
                        st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Connection form ──
        db_type = st.session_state.db_type_sel
        meta    = DB_TYPES[db_type]

        st.markdown(
            f'<div class="section-header">{meta["icon"]} <span>{db_type} Connection</span>'
            f'<span class="section-badge">CONFIGURE</span></div>',
            unsafe_allow_html=True
        )

        with st.form("db_connect_form"):
            params = {}

            if db_type == "SQLite":
                params["filepath"] = st.text_input(
                    "Database File Path",
                    value=st.session_state.db_params.get("filepath", ""),
                    placeholder="C:/path/to/database.db  or  :memory:",
                    help="Full path to the SQLite .db file, or :memory: for in-memory"
                )
            else:
                c1, c2 = st.columns([3, 1])
                with c1:
                    params["host"] = st.text_input(
                        "Host", value=st.session_state.db_params.get("host", ""),
                        placeholder="db.example.com  or  localhost"
                    )
                with c2:
                    params["port"] = st.text_input(
                        "Port", value=st.session_state.db_params.get("port", str(meta["default_port"] or "")),
                    )
                params["database"] = st.text_input(
                    "Database Name", value=st.session_state.db_params.get("database", ""),
                    placeholder="my_database"
                )
                params["username"] = st.text_input(
                    "Username", value=st.session_state.db_params.get("username", ""),
                )
                params["password"] = st.text_input(
                    "Password", type="password",
                    value=st.session_state.db_params.get("password", ""),
                )

                if db_type == "PostgreSQL":
                    params["ssl_mode"] = st.selectbox(
                        "SSL Mode",
                        ["disable", "require", "verify-ca", "verify-full"],
                        index=["disable", "require", "verify-ca", "verify-full"].index(
                            st.session_state.db_params.get("ssl_mode", "disable")
                        ),
                    )

                if db_type == "SQL Server":
                    params["odbc_driver"] = st.text_input(
                        "ODBC Driver",
                        value=st.session_state.db_params.get("odbc_driver", "ODBC Driver 17 for SQL Server"),
                    )

            # Advanced options expander
            with st.expander("⚙️ Advanced Options"):
                params["pool_size"]  = st.number_input("Connection Pool Size", min_value=1, max_value=20, value=5)
                params["timeout"]    = st.number_input("Query Timeout (s)", min_value=5, max_value=600, value=30)
                params["read_only"]  = st.checkbox("Read-Only Mode (no write-back)", value=False)

            col_test, col_save = st.columns(2)
            with col_test:
                test_btn = st.form_submit_button("⚡ Test Connection", use_container_width=True)
            with col_save:
                save_btn = st.form_submit_button("💾 Save & Connect", type="primary", use_container_width=True)

        # Handle form submission
        if test_btn or save_btn:
            st.session_state.db_params = params
            connector = DatabaseConnector(db_type, params)
            ok, msg = connector.connect()
            if ok:
                if save_btn:
                    st.session_state.db_connector = connector
                    st.session_state.db_tables    = connector.list_tables()
                    # Init NL agent
                    try:
                        llm = LMStudioClient()
                        st.session_state.nl_agent = NLQueryAgent(llm)
                    except Exception:
                        st.session_state.nl_agent = NLQueryAgent()
                st.success(f"✅ {msg}")
                if save_btn:
                    st.rerun()
            else:
                st.error(f"❌ {msg}")
                st.info(f"Make sure the `{meta['pip_package']}` driver is installed: `pip install {meta['pip_package']}`")

# ════════════════════════════════════════════════════════════════
# RIGHT PANEL — Table browser + Studio
# ════════════════════════════════════════════════════════════════
with col_right:
    if not st.session_state.db_connector or not st.session_state.db_connector.is_connected:
        st.markdown("""
        <div class="glass-panel" style="text-align:center;padding:3rem;margin-top:3rem">
          <div style="font-size:3rem;margin-bottom:1rem">🗄️</div>
          <div style="font-size:1.1rem;font-weight:600;color:#94a3b8;margin-bottom:0.5rem">
            No Database Connected
          </div>
          <div style="font-size:0.85rem;color:#475569">
            Select a database type on the left and fill in the connection details to get started.
          </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        connector = st.session_state.db_connector
        tables    = st.session_state.db_tables

        # ── Table browser ──
        st.markdown('<div class="section-header">📋 <span>Tables</span>'
                    f'<span class="section-badge">{len(tables)} found</span></div>',
                    unsafe_allow_html=True)

        if not tables:
            st.info("No tables found in this database. Check permissions or database name.")
        else:
            # Refresh tables button
            if st.button("🔄 Refresh Tables", key="refresh_tables"):
                st.session_state.db_tables = connector.list_tables()
                st.rerun()

            # Table list
            for tbl in tables[:30]:  # show max 30
                active_class = "active" if st.session_state.active_table == tbl else ""
                col_tbl, col_sel = st.columns([4, 1])
                with col_tbl:
                    try:
                        info = connector.get_table_info(tbl)
                        rc = info.get("row_count", "?")
                        nc = len(info.get("columns", []))
                    except Exception:
                        rc, nc = "?", "?"
                        
                    rc_str = f"{rc:,}" if isinstance(rc, int) else str(rc)
                    
                    st.markdown(f"""
                    <div class="table-card {active_class}">
                      <div>
                        <span style="font-weight:600;color:#e2e8f0">📊 {tbl}</span>
                        <span style="font-size:0.72rem;color:#64748b;margin-left:8px">{rc_str} rows · {nc} cols</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_sel:
                    if st.button("Open →", key=f"open_{tbl}"):
                        st.session_state.active_table  = tbl
                        st.session_state.table_schema  = connector.get_table_info(tbl)
                        st.session_state.table_df      = None  # lazy load
                        st.session_state.nl_query_result = None
                        st.session_state.pending_sql   = None
                        st.session_state.suggest_queries = []
                        st.rerun()

        # ── Table studio (when a table is selected) ──
        if st.session_state.active_table:
            tbl    = st.session_state.active_table
            schema = st.session_state.table_schema

            schema_rc = schema.get('row_count', '?')
            schema_rc_str = f"{schema_rc:,}" if isinstance(schema_rc, int) else str(schema_rc)
            
            st.markdown(f"""
            <div class="glass-panel success" style="display:flex;align-items:center;gap:12px;padding:0.8rem 1.2rem;margin-top:1.5rem">
              <span style="font-size:1.5rem">📊</span>
              <div>
                <div style="font-weight:700;color:#4ade80;font-size:0.95rem">{tbl}</div>
                <div style="font-size:0.75rem;color:#64748b">
                  {schema_rc_str} rows · {len(schema.get('columns',[]))} columns · 
                  PK: {', '.join(schema.get('pk_columns',[])) or 'none'}
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Studio tabs
            tab_preview, tab_profile, tab_clean, tab_query, tab_history = st.tabs([
                "👁️ Preview & Schema",
                "📊 Data Health Profiler",
                "🤖 AI Cleaning",
                "💬 NL Query Console",
                "📋 Query History",
            ])

            # ────────────────────────────────────────
            # Tab 1: Preview + Schema
            # ────────────────────────────────────────
            with tab_preview:
                c_prev, c_schema_info = st.columns(2)
                with c_prev:
                    st.markdown("**Table Schema**")
                    cols_data = schema.get("columns", [])
                    if cols_data:
                        schema_df = pd.DataFrame(cols_data)
                        st.dataframe(schema_df, use_container_width=True, height=280)

                with c_schema_info:
                    st.markdown("**Quick Stats**")
                    rc = schema.get("row_count", 0)
                    nc = len(schema.get("columns", []))
                    pk = schema.get("pk_columns", [])
                    st.metric("Total Rows", f"{rc:,}")
                    st.metric("Total Columns", nc)
                    st.metric("Primary Keys", len(pk))
                    if pk:
                        st.caption(f"PK columns: {', '.join(pk)}")

                st.markdown("**Data Preview**")
                n_rows = st.slider("Rows to preview", 5, 200, 20, key="prev_rows")
                if st.button("Load Preview", key="load_prev"):
                    with st.spinner("Loading..."):
                        try:
                            df = connector.load_table(tbl, limit=n_rows)
                            st.session_state.table_df = df
                        except Exception as e:
                            st.error(f"Error: {e}")

                if st.session_state.table_df is not None:
                    st.dataframe(st.session_state.table_df, use_container_width=True, height=350)

                    # Missing values quick view
                    df = st.session_state.table_df
                    missing = df.isna().sum()
                    if missing.sum() > 0:
                        st.markdown("**Missing Values**")
                        m_df = pd.DataFrame({
                            "Column":    missing.index,
                            "Missing":   missing.values,
                            "Missing %": (missing.values / len(df) * 100).round(1),
                        }).query("Missing > 0")
                        st.dataframe(m_df, use_container_width=True)

            # ────────────────────────────────────────
            # Tab 1.5: Health Profiler
            # ────────────────────────────────────────
            with tab_profile:
                st.markdown("### 📊 Database Health Profiler")
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
                                    
                                    comp_df = pd.DataFrame(changes).drop_duplicates().reset_index(drop=True)
                                    st.dataframe(comp_df, use_container_width=True)
                                elif clusters:
                                    fuzzy_count = sum(c["cluster_size"] for c in clusters)
                                    st.warning(f"⚠️ Found {fuzzy_count} records in {len(clusters)} fuzzy clusters, but no text differences detected (likely exact matches).")
                                else:
                                    st.success("✅ No fuzzy duplicates detected!")
                                    
                        except Exception as e:
                            st.error(f"Error during profiling: {e}")

            # ────────────────────────────────────────
            # Tab 2: AI Cleaning Pipeline
            # ────────────────────────────────────────
            with tab_clean:
                st.markdown("""
                <div class="glass-panel info" style="font-size:0.85rem">
                  <b style="color:#22d3ee">🤖 AI Cleaning Pipeline</b><br>
                  Run the full 12-phase IntelliClean pipeline on this database table.
                  The pipeline will detect domain, classify schema, fix missing values,
                  remove duplicates, handle outliers, and optionally write the cleaned
                  data back to a new table in the same database.
                </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    row_limit = st.number_input(
                        "Row limit (0 = all rows)", min_value=0, max_value=1_000_000, value=0,
                        help="Limit the number of rows to clean. 0 = entire table."
                    )
                with c2:
                    write_back = st.checkbox("Write cleaned data back to DB", value=False)
                    if write_back:
                        write_back_table = st.text_input(
                            "Write-back table name",
                            value=f"{tbl}_cleaned"
                        )
                        write_mode = st.selectbox("If table exists", ["replace", "append", "fail"])

                if st.button("🚀 Start AI Cleaning on Table", type="primary", use_container_width=True):
                    import importlib
                    import backend.loader
                    import backend.pipeline
                    import backend.exporter
                    importlib.reload(backend.loader)
                    importlib.reload(backend.pipeline)
                    importlib.reload(backend.exporter)
                    from backend.loader import UniversalLoader
                    from backend.pipeline import PipelineOrchestrator
                    from backend.exporter import Exporter
                    import tempfile

                    logs_placeholder = st.empty()
                    logs = []

                    def db_log(msg):
                        logs.append(msg)
                        colored = []
                        for line in logs[-30:]:
                            if "Error" in line or "FAILED" in line:
                                colored.append(f'<span style="color:#f87171">{line}</span>')
                            elif "[DB Pipeline]" in line:
                                colored.append(f'<span style="color:#22d3ee">{line}</span>')
                            elif "Phase" in line:
                                colored.append(f'<span style="color:#a78bfa;font-weight:600">{line}</span>')
                            else:
                                colored.append(line)
                        logs_placeholder.markdown(
                            '<div style="background:#060810;border:1px solid rgba(255,255,255,0.06);'
                            'border-radius:10px;padding:1rem;font-family:monospace;font-size:0.78rem;'
                            'color:#94a3b8;max-height:320px;overflow-y:auto;white-space:pre-wrap">'
                            + "<br>".join(colored) + "</div>",
                            unsafe_allow_html=True
                        )

                    try:
                        backup_dir = tempfile.mkdtemp()
                        exporter = Exporter()
                        backup_info = exporter.create_db_backup(connector, tbl, backup_dir=backup_dir)

                        loader = UniversalLoader.from_database(
                            connector, 
                            tbl, 
                            limit=row_limit if row_limit > 0 else 100_000
                        )
                        df_raw = loader.load_and_optimize()
                        
                        db_orch = PipelineOrchestrator(
                            df=df_raw,
                            log_callback=db_log
                        )
                        cleaned_df, meta = db_orch.execute()
                        
                        if write_back:
                            wb_table = write_back_table if write_back_table else f"{tbl}_cleaned"
                            wb_mode = write_mode if write_mode else "replace"
                            ok, msg = exporter.write_to_database(cleaned_df, connector, wb_table, if_exists=wb_mode)
                            meta["write_back_status"] = "success" if ok else f"failed: {msg}"
                        
                        meta["backup_info"] = backup_info
                        st.session_state.cleaning_result = {"df": cleaned_df, "meta": meta}

                        # ── METRICS ROW ──
                        validation = meta.get("validation", {})
                        missing_before = sum(v for v in meta.get("missing_values_before", {}).values() if isinstance(v, (int, float)))
                        dedup_count = len(set(c.get("Corrected","") for c in meta.get("dedup_changes", [])))
                        confidence  = validation.get("overall_confidence", 0)
                        domain      = meta.get("domain", "Generic")
                        domain_info = meta.get("domain_info", {})
                        domain_conf = domain_info.get("confidence", "")
                        domain_method = domain_info.get("method", "")
                        domain_reason = domain_info.get("reasoning", "")

                        st.markdown(f"""
                        <div class="metric-grid" style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1rem">
                          <div class="glass-panel" style="border-left:4px solid #a855f7;padding:1rem">
                            <div style="font-size:0.75rem;color:#94a3b8;font-weight:600;text-transform:uppercase">Original Rows</div>
                            <div style="font-size:1.6rem;font-weight:800;color:#e2e8f0">{meta.get('initial_rows',0):,}</div>
                          </div>
                          <div class="glass-panel" style="border-left:4px solid #22d3ee;padding:1rem">
                            <div style="font-size:0.75rem;color:#94a3b8;font-weight:600;text-transform:uppercase">Cleaned Rows</div>
                            <div style="font-size:1.6rem;font-weight:800;color:#e2e8f0">{meta.get('final_rows',0):,}</div>
                          </div>
                          <div class="glass-panel" style="border-left:4px solid #4ade80;padding:1rem">
                            <div style="font-size:0.75rem;color:#94a3b8;font-weight:600;text-transform:uppercase">AI Confidence</div>
                            <div style="font-size:1.6rem;font-weight:800;color:#e2e8f0">{confidence:.0f}%</div>
                          </div>
                          <div class="glass-panel" style="border-left:4px solid #ec4899;padding:1rem">
                            <div style="font-size:0.75rem;color:#94a3b8;font-weight:600;text-transform:uppercase">Domain</div>
                            <div style="font-size:1.2rem;font-weight:700;color:#e2e8f0">{domain}</div>
                            <div style="font-size:0.7rem;color:#64748b">{domain_conf}</div>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)

                        if meta.get("backup_info"):
                            bi = meta["backup_info"]
                            st.markdown(f"""
                            <div class="glass-panel warning" style="font-size:0.83rem;margin-bottom:1rem">
                              <b>🗄️ Backup Created Before Write-Back</b><br>
                              {"Backup Table: " + str(bi.get('backup_table','')) + "<br>" if bi.get('backup_table') else ""}
                              {"Backup CSV: " + str(bi.get('backup_csv','')) if bi.get('backup_csv') else ""}
                            </div>
                            """, unsafe_allow_html=True)

                        if domain_reason:
                            st.markdown(f"""
                            <div class="glass-panel" style="display:flex;align-items:center;gap:10px;padding:0.7rem 1.2rem;margin-bottom:1.5rem">
                              <span style="font-size:1.2rem">🤖</span>
                              <span style="font-size:0.85rem;color:#94a3b8"><b style="color:#a78bfa">Domain AI Reasoning:</b> {domain_reason}</span>
                            </div>
                            """, unsafe_allow_html=True)

                        # ── TABBED RESULTS ──
                        t_prev, t_sch, t_ml, t_imp, t_dedup, t_curr, t_aud = st.tabs([
                            "📊 Cleaned Data", "🧠 Schema", "🌐 Multilingual", "🧩 Imputation", "🔗 Deduplication", "💱 Currency", "📋 Audit"
                        ])

                        with t_prev:
                            st.dataframe(cleaned_df.head(100), use_container_width=True, height=420)
                            csv_bytes = cleaned_df.to_csv(index=False).encode()
                            st.download_button("📥 Download Cleaned Data (CSV)", data=csv_bytes, file_name=f"{tbl}_cleaned.csv", mime="text/csv")
                        
                        with t_sch:
                            schema_map = meta.get("schema_mapping", {})
                            strats  = meta.get("strategies", {})
                            if schema_map:
                                rows = []
                                for col, info in schema_map.items():
                                    strat = strats.get(col, {})
                                    rows.append({
                                        "Column": col,
                                        "Semantic Type": info.get("semantic_type", "?"),
                                        "Multilingual": "✅ Yes" if info.get("needs_multilingual") else "— No",
                                        "Imputation": info.get("imputation_strategy", strat.get("imputation", "leave_empty")),
                                        "AI Reasoning": info.get("imputation_reasoning", ""),
                                    })
                                st.dataframe(pd.DataFrame(rows), use_container_width=True)
                            else:
                                st.info("No schema information available.")

                        with t_ml:
                            stats = meta.get("translation_stats", {})
                            if stats:
                                for col, data in stats.items():
                                    st.write(f"**{col}**: ASCII normalized: {data.get('ascii_normalized',0)} | LLM processed: {data.get('llm_translated', data.get('items_processed',0))}")
                            else:
                                st.info("No multilingual processing was required.")

                        with t_imp:
                            rules = meta.get("smart_imputation_rules", [])
                            stats_log = meta.get("statistical_imputation_log", [])
                            if rules:
                                st.write("**Smart AI Contextual Rules:**")
                                st.json(rules)
                            if stats_log:
                                st.write("**Statistical Fallbacks:**")
                                st.json(stats_log)
                            if not rules and not stats_log:
                                st.success("No missing values were found in the dataset.")
                                
                        with t_dedup:
                            removed = meta.get("initial_rows", 0) - meta.get("final_rows", 0)
                            clusters = meta.get("dedup_cluster_report", [])
                            changes = meta.get("dedup_changes", [])
                            
                            if removed > 0 or clusters:
                                st.warning(f"⚠️ **Removed {removed} duplicate rows.**")
                                if changes:
                                    st.write("**Name/Entity Corrections (Detected Fuzzy Duplicated Values):**")
                                    st.dataframe(pd.DataFrame(changes).drop_duplicates(), use_container_width=True)
                            else:
                                st.success("✅ No duplicates detected.")
                                
                        with t_curr:
                            curr_rep = meta.get("currency_report", [])
                            if curr_rep:
                                st.json(curr_rep)
                            else:
                                st.success("No currency conversion needed.")
                                
                        with t_aud:
                            exps = meta.get("explanations", [])
                            if exps:
                                st.write("**Audit Trail (Top 50 Transformations):**")
                                st.dataframe(pd.DataFrame(exps[:50]), use_container_width=True)
                            else:
                                st.info("No column-level string transformations required audit explanations.")
                    except Exception as e:
                        st.error(f"Pipeline error: {e}")
                        import traceback
                        st.code(traceback.format_exc())

            # ────────────────────────────────────────
            # Tab 3: NL Query Console
            # ────────────────────────────────────────
            with tab_query:
                st.markdown("""
                <div class="glass-panel info" style="font-size:0.85rem;margin-bottom:1rem">
                  <b style="color:#22d3ee">💬 Natural Language Query Console</b><br>
                  Type your query in plain English. The AI will generate the SQL, explain it,
                  and safely execute it — with <b>automatic backup</b> before any write operations.
                </div>
                """, unsafe_allow_html=True)

                # Suggested queries
                if not st.session_state.suggest_queries:
                    if st.button("✨ Generate AI Query Suggestions", key="gen_suggest"):
                        nl_agent = st.session_state.nl_agent
                        if nl_agent:
                            with st.spinner("Generating smart query suggestions..."):
                                st.session_state.suggest_queries = nl_agent.suggest_cleaning_queries(
                                    schema, db_type=connector.db_type
                                )
                            st.rerun()
                        else:
                            st.warning("NL Agent not initialized. Check LLM connection.")
                else:
                    st.markdown("**💡 Smart Suggestions** (click to use)")
                    cats = {}
                    for q in st.session_state.suggest_queries:
                        cat = q.get("category", "General")
                        cats.setdefault(cat, []).append(q)

                    for cat, queries in cats.items():
                        st.markdown(f"<small style='color:#64748b;font-weight:600'>{cat}</small>", unsafe_allow_html=True)
                        cols_sugg = st.columns(min(len(queries), 3))
                        for idx, q in enumerate(queries[:3]):
                            with cols_sugg[idx]:
                                if st.button(f"📌 {q['label']}", key=f"sugg_{cat}_{idx}", use_container_width=True):
                                    st.session_state["nl_prefill"] = q["label"]
                                    st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)

                # NL input
                nl_input = st.text_area(
                    "Type your query in plain English",
                    value=st.session_state.pop("nl_prefill", ""),
                    placeholder=(
                        "Examples:\n"
                        "• Show me all duplicate records by email\n"
                        "• Find rows where phone number is missing\n"
                        "• Count records grouped by city\n"
                        "• Delete rows where both name and email are null\n"
                        "• Update all lowercase emails to uppercase\n"
                        "• Show top 10 customers by purchase amount"
                    ),
                    height=110,
                    key="nl_input_area"
                )

                col_gen, col_raw = st.columns([2, 1])
                with col_gen:
                    gen_sql_btn = st.button("🧠 Generate SQL", type="primary", use_container_width=True, key="gen_sql")
                with col_raw:
                    raw_sql_mode = st.checkbox("Raw SQL mode", value=False, key="raw_sql_toggle")

                # Raw SQL mode
                if raw_sql_mode:
                    raw_sql_input = st.text_area(
                        "Enter SQL directly",
                        placeholder=f'SELECT * FROM "{tbl}" WHERE ...',
                        height=100, key="raw_sql_input"
                    )
                    if st.button("▶️ Execute SQL", key="exec_raw"):
                        if raw_sql_input.strip():
                            meta_for_raw = {
                                "sql":            raw_sql_input,
                                "is_destructive": connector.is_destructive(raw_sql_input),
                                "affected_tables": [tbl],
                            }
                            st.session_state.nl_query_result = meta_for_raw
                            st.session_state.pending_sql     = raw_sql_input
                            st.rerun()

                # Generate SQL from NL
                if gen_sql_btn and nl_input.strip():
                    nl_agent = st.session_state.nl_agent
                    if not nl_agent:
                        try:
                            llm = LMStudioClient()
                            st.session_state.nl_agent = NLQueryAgent(llm)
                            nl_agent = st.session_state.nl_agent
                        except Exception as e:
                            st.error(f"LLM client error: {e}")
                            nl_agent = None

                    if nl_agent:
                        with st.spinner("🧠 LLM is generating SQL..."):
                            sample_df = None
                            try:
                                sample_df = connector.load_table(tbl, limit=3)
                            except Exception:
                                pass
                            
                            sample_data_str = sample_df.to_markdown() if sample_df is not None and not sample_df.empty else ""
                            all_tables = connector.list_tables()
                            
                            result = nl_agent.generate_sql(
                                user_query=nl_input.strip(),
                                table_schema=schema,
                                db_type=connector.db_type,
                                sample_data=sample_data_str,
                                all_tables=all_tables
                            )
                        st.session_state.nl_query_result = result
                        st.session_state.pending_sql     = result["sql"]
                        st.rerun()

                # Show generated SQL + execution panel
                result = st.session_state.nl_query_result
                if result:
                    st.markdown('<div class="section-header">⚡ <span>Generated Query</span></div>', unsafe_allow_html=True)

                    # Confidence badge
                    conf = result.get("confidence", "Medium")
                    conf_color = {"High": "#4ade80", "Medium": "#fbbf24", "Low": "#f87171"}.get(conf, "#94a3b8")
                    st.markdown(
                        f'<span style="font-size:0.78rem;color:{conf_color};font-weight:600">'
                        f'AI Confidence: {conf}</span>',
                        unsafe_allow_html=True
                    )

                    # Explanation
                    if result.get("explanation"):
                        st.markdown(
                            f'<div class="glass-panel" style="font-size:0.85rem;margin:0.5rem 0">'
                            f'<b>📖 Explanation:</b> {result["explanation"]}</div>',
                            unsafe_allow_html=True
                        )

                    # SQL preview (editable)
                    edited_sql = st.text_area(
                        "SQL (you can edit before executing)",
                        value=st.session_state.pending_sql,
                        height=140,
                        key="sql_edit"
                    )
                    st.session_state.pending_sql = edited_sql

                    # Safety warning for destructive ops
                    is_dest = connector.is_destructive(edited_sql)
                    if is_dest:
                        st.markdown(f"""
                        <div class="glass-panel warning" style="font-size:0.85rem">
                          <b>⚠️ Destructive Operation Detected</b><br>
                          This SQL will modify data. A <b>backup will be created automatically</b>
                          (table-copy + CSV) before execution.<br>
                          <small style="color:#94a3b8">Affected table(s): {', '.join(result.get('affected_tables', [tbl]))}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        confirm = st.checkbox("✅ I understand — proceed with backup and execute", key="dest_confirm")
                    else:
                        confirm = True

                    col_exec, col_clear = st.columns([2, 1])
                    with col_exec:
                        exec_btn = st.button(
                            "▶️ Execute Query",
                            type="primary",
                            disabled=is_dest and not confirm,
                            use_container_width=True,
                            key="exec_nl_sql"
                        )
                    with col_clear:
                        if st.button("✖️ Clear", key="clear_nl", use_container_width=True):
                            st.session_state.nl_query_result = None
                            st.session_state.pending_sql     = None
                            st.session_state.last_exec_result = None
                            st.rerun()

                    if exec_btn:
                        st.session_state.query_run_count = st.session_state.get("query_run_count", 0) + 1
                        nl_agent = st.session_state.nl_agent
                        if not nl_agent:
                            nl_agent = NLQueryAgent()
                            st.session_state.nl_agent = nl_agent

                        import tempfile
                        backup_dir = tempfile.mkdtemp()

                        with st.spinner("Executing..."):
                            exec_result = nl_agent.execute_with_backup(
                                connector  = connector,
                                sql        = edited_sql,
                                query_meta = result,
                                backup_dir = backup_dir,
                                user_query = nl_input,
                                table_schema = schema
                            )
                            st.session_state.last_exec_result = exec_result

                            if exec_result["success"]:
                                st.session_state.query_history.append({
                                    "nl_query":  nl_input,
                                    "sql":       edited_sql,
                                    "rows":      exec_result["rows_affected"],
                                    "time":      exec_result["execution_time"],
                                    "backups":   exec_result["backups"],
                                    "status":    "success",
                                })

                    exec_result = st.session_state.get("last_exec_result")
                    if exec_result:
                        if exec_result["success"]:
                            # Show backups created
                            if exec_result["backups"]:
                                for b in exec_result["backups"]:
                                    bak_msgs = []
                                    if b.get("backup_table"):
                                        bak_msgs.append(f"Table copy: `{b['backup_table']}`")
                                    if b.get("csv_path"):
                                        bak_msgs.append(f"CSV: `{b['csv_path']}`")
                                    st.markdown(
                                        f'<div class="backup-badge">🗄️ Backup: {" · ".join(bak_msgs)}</div>',
                                        unsafe_allow_html=True
                                    )

                            if exec_result["result_df"] is not None:
                                df = exec_result["result_df"]
                                st.success(
                                    f"✅ Query returned {len(df)} rows in {exec_result['execution_time']}s"
                                )
                                
                                # Editable dataframe so user can correct values manually
                                edited_df = st.data_editor(
                                    df, 
                                    use_container_width=True, 
                                    height=360, 
                                    num_rows="dynamic",
                                    key=f"sql_data_editor_{st.session_state.get('query_run_count', 0)}"
                                )
                                
                                st.markdown("---")
                                st.markdown('<div style="font-size:0.9rem;font-weight:600;margin-bottom:10px">💾 Save Corrections to Database</div>', unsafe_allow_html=True)
                                c_table, c_mode, c_btn = st.columns([2, 1, 1])
                                with c_table:
                                    save_tgt = st.text_input("Target Table Name", value=tbl + "_cleaned", key="save_edit_tgt")
                                with c_mode:
                                    save_mode = st.selectbox("If exists", ["fail", "append", "replace"], key="save_edit_mode")
                                
                                replace_confirmed = True
                                if save_tgt in st.session_state.db_tables and save_mode == "replace":
                                    st.error("⚠️ **Destructive Action:** 'Replace' mode will DROP the existing table. This destroys primary keys, constraints, and indexes.")
                                    replace_confirmed = st.checkbox("I understand. Drop and recreate the table.", key="confirm_replace_writeback")

                                with c_btn:
                                    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
                                    apply_disabled = (save_tgt in st.session_state.db_tables and save_mode == "replace" and not replace_confirmed)
                                    if st.button("Apply Changes", type="primary", use_container_width=True, disabled=apply_disabled):
                                        with st.spinner("Saving to database..."):
                                            # Create backup if replacing original table
                                            if save_tgt == tbl and save_mode == "replace":
                                                ok_b, b_name = connector.create_backup(tbl)
                                                if ok_b:
                                                    st.info(f"🗄️ Backup created before overwrite: `{b_name}`")
                                            ok_w, msg_w = connector.write_dataframe(edited_df, save_tgt, if_exists=save_mode)
                                            if ok_w:
                                                st.success(f"✅ Successfully saved edits to `{save_tgt}`!")
                                            else:
                                                st.error(f"❌ Failed to save: {msg_w}")

                                # Download
                                csv_bytes = df.to_csv(index=False).encode()
                                st.download_button(
                                    "📥 Download Results (CSV)",
                                    data=csv_bytes,
                                    file_name="query_result.csv",
                                    mime="text/csv",
                                )
                            else:
                                st.success(
                                    f"✅ Query executed successfully in {exec_result['execution_time']}s"
                                )
                        else:
                            st.error(f"❌ Execution failed: {exec_result['error']}")
                            st.session_state.query_history.append({
                                "nl_query": nl_input,
                                "sql":      edited_sql,
                                "status":   "failed",
                                "error":    exec_result["error"],
                            })

            # ────────────────────────────────────────
            # Tab 4: Query History & Audit Log
            # ────────────────────────────────────────
            with tab_history:
                history = st.session_state.query_history
                if not history:
                    st.markdown("""
                    <div class="glass-panel" style="text-align:center;padding:2rem">
                      <div style="font-size:2rem;margin-bottom:0.5rem">📋</div>
                      <div style="color:#64748b;font-size:0.9rem">No queries executed yet in this session.</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    col_h1, col_h2 = st.columns([3, 1])
                    with col_h1:
                        st.markdown(f"**{len(history)} queries in this session**")
                    with col_h2:
                        if st.button("Clear History", key="clear_hist"):
                            st.session_state.query_history = []
                            st.rerun()

                    for i, h in enumerate(reversed(history)):
                        status_color = "#4ade80" if h.get("status") == "success" else "#f87171"
                        status_icon  = "✅" if h.get("status") == "success" else "❌"
                        with st.expander(
                            f"{status_icon} {h.get('nl_query', h.get('sql', 'Query'))[:60]}...",
                            expanded=(i == 0)
                        ):
                            st.markdown(f"""
                            <div class="hist-item">
                              <div style="color:{status_color};font-weight:600;margin-bottom:4px">
                                {status_icon} {h['status'].upper()}
                              </div>
                              {"<div style='color:#94a3b8;font-size:0.8rem;margin-bottom:4px'><b>Query:</b> " + h.get('nl_query','') + "</div>" if h.get('nl_query') else ""}
                              <div style="font-family:monospace;font-size:0.78rem;color:#a5f3fc;
                                   background:#060810;padding:8px;border-radius:6px;margin-bottom:4px">
                                {h.get('sql','').replace(chr(10),'<br>')}
                              </div>
                              {"<div style='color:#64748b;font-size:0.76rem'>Rows: " + str(h.get('rows','?')) + " · Time: " + str(h.get('time','?')) + "s</div>" if h.get('rows') is not None else ""}
                              {"<div style='color:#f87171;font-size:0.76rem'>Error: " + str(h.get('error','')) + "</div>" if h.get('error') else ""}
                            </div>
                            """, unsafe_allow_html=True)

                            for b in h.get("backups", []):
                                if b.get("backup_table") or b.get("csv_path"):
                                    st.markdown(
                                        f'<span class="backup-badge">🗄️ Backup: '
                                        f'{b.get("backup_table","")} · {b.get("csv_path","")}</span>',
                                        unsafe_allow_html=True
                                    )

                    # Export audit log
                    if st.button("📤 Export Audit Log (JSON)", key="export_audit"):
                        import json
                        audit_json = json.dumps(history, indent=2, default=str)
                        st.download_button(
                            "Download Audit Log",
                            data=audit_json.encode(),
                            file_name="query_audit_log.json",
                            mime="application/json",
                        )
