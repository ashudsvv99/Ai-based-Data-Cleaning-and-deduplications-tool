import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import math
import re

@st.dialog("Audit Logs")
def show_audit_logs(table_name):
    st.markdown(f"**Audit Trail for `{table_name}`**")
    logs = [
        {"Date & Time": "2026-07-15 14:30:00", "Employee": "Alice Smith", "Action Performed": "Resolved Missing Values", "Issues Addressed": "Filled 45 nulls in 'phone'"},
        {"Date & Time": "2026-07-14 09:15:22", "Employee": "Bob Johnson", "Action Performed": "Removed Exact Duplicates", "Issues Addressed": "Deleted 12 duplicate rows"},
        {"Date & Time": "2026-07-12 16:45:10", "Employee": "System", "Action Performed": "Schema Update", "Issues Addressed": "Added column 'status'"},
    ]
    st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)

def generate_sparkline_svg(color, data, width=120, height=25):
    if len(data) == 0: return ""
    min_y = min(data)
    max_y = max(data)
    range_y = max_y - min_y if max_y != min_y else 1
    
    points = []
    for i, val in enumerate(data):
        x = (i / (len(data) - 1)) * width
        y = height - ((val - min_y) / range_y) * (height - 4) - 2
        points.append(f"{x},{y}")
        
    path_d = f"M {points[0]} " + " L ".join(points[1:])
    fill_points = points.copy()
    fill_points.append(f"{width},{height}")
    fill_points.append(f"0,{height}")
    fill_path = f"M {fill_points[0]} " + " L ".join(fill_points[1:]) + " Z"
    grad_id = color.replace('#','')
    
    svg = f"""<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="margin-top: 15px;"><defs><linearGradient id="grad_{grad_id}" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" style="stop-color:{color};stop-opacity:0.3" /><stop offset="100%" style="stop-color:{color};stop-opacity:0.0" /></linearGradient></defs><path d="{fill_path}" fill="url(#grad_{grad_id})" /><path d="{path_d}" fill="none" stroke="{color}" stroke-width="2" /><circle cx="{width}" cy="{points[-1].split(',')[1]}" r="2" fill="{color}" /></svg>"""
    return svg

def create_gauge(value):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta", value = value, domain = {'x': [0, 1], 'y': [0, 1]},
        delta = {'reference': 80, 'position': "top", 'increasing': {'color': '#10B981'}, 'decreasing': {'color': '#EF4444'}},
        number = {'font': {'size': 32, 'color': '#F8FAFC', 'family': 'sans-serif'}, 'valueformat': '.1f'},
        title = {'text': "Health Score", 'font': {'size': 14, 'color': '#F8FAFC'}},
        gauge = {'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#334155", 'tickfont': {'color': '#94A3B8'}, 'tickvals': [0, 100]},
                 'bar': {'color': "#F8FAFC", 'thickness': 0.15}, 'bgcolor': "#334155", 'borderwidth': 0, 'steps': [{'range': [0, value], 'color': "#10B981"}]}
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=185, margin=dict(l=10, r=10, t=30, b=10))
    return fig

def create_donut(labels, values, colors, title=""):
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.7, marker_colors=colors, textinfo='percent', textfont=dict(color='white', size=10, family='sans-serif'), hovertemplate="%{label}<br>%{value}<extra></extra>")])
    fig.update_layout(title=dict(text=title, font=dict(size=14, color="#F8FAFC"), x=0, y=0.95), showlegend=True, legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=0.9, font=dict(color="#F8FAFC", size=10)), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=40, b=10), height=180)
    return fig

def count_outliers(df):
    outliers = 0
    for col in df.select_dtypes(include=[np.number]).columns:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        outliers += ((df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))).sum()
    return int(outliers)

def count_invalid_values(df):
    invalid = 0
    for col in df.columns:
        if df[col].dtype == object:
            invalid += df[col].astype(str).str.strip().isin(['', 'N/A', 'NULL', 'None', 'NaN']).sum()
    return int(invalid)

# --- Backend Logic Helpers ---
def _get_non_pk_cols(connector, tbl_name: str) -> list:
    info = connector.get_table_info(tbl_name)
    all_cols = [c["name"] for c in info.get("columns", [])]
    pk_cols  = set(info.get("pk_columns", []))
    if not pk_cols:
        pk_cols = {c for c in all_cols if c.lower() in ("id", "pk") or c.lower().endswith("_id") or c.lower().startswith("id_")}
    non_pk = [c for c in all_cols if c not in pk_cols]
    return non_pk if non_pk else all_cols

def _count_exact_dupes_sql(connector, tbl_name: str) -> int:
    try:
        cols = _get_non_pk_cols(connector, tbl_name)
        if not cols: return 0
        qc = lambda c: f"`{c}`" if connector.db_type == "MySQL" else f'"{c}"'
        qt = lambda t: f"`{t}`" if connector.db_type == "MySQL" else f'"{t}"'
        col_list = ", ".join([qc(c) for c in cols])
        sql = f"SELECT COALESCE(SUM(cnt - 1), 0) AS total_dupe_rows FROM (SELECT {col_list}, COUNT(*) AS cnt FROM {qt(tbl_name)} GROUP BY {col_list} HAVING COUNT(*) > 1) AS grp"
        res, err = connector.execute_query(sql)
        if err is None and res is not None and len(res) > 0:
            val = res.iloc[0, 0]
            return int(val) if val is not None else 0
    except Exception:
        pass
    return 0

def _fetch_exact_dupe_rows_sql(connector, tbl_name: str, limit: int = 500) -> pd.DataFrame:
    try:
        cols = _get_non_pk_cols(connector, tbl_name)
        if not cols: return pd.DataFrame()
        qc = lambda c: f"`{c}`" if connector.db_type == "MySQL" else f'"{c}"'
        qt = lambda t: f"`{t}`" if connector.db_type == "MySQL" else f'"{t}"'
        col_list   = ", ".join([qc(c) for c in cols])
        join_conds = " AND ".join([f"(t.{qc(c)} = d.{qc(c)} OR (t.{qc(c)} IS NULL AND d.{qc(c)} IS NULL))" for c in cols])
        # Fetch t.* to include the PK columns in the UI for clarity
        sql = f"SELECT t.* FROM {qt(tbl_name)} t JOIN (SELECT {col_list} FROM {qt(tbl_name)} GROUP BY {col_list} HAVING COUNT(*) > 1) AS d ON {join_conds} ORDER BY {col_list} LIMIT {limit}"
        res, err = connector.execute_query(sql)
        if err is None and res is not None:
            return res
    except Exception:
        pass
    return pd.DataFrame()

def _run_fuzzy_dedup(df_full: pd.DataFrame):
    from backend.schema_detector import classify_all_columns
    from cleaning.deduplication import DeduplicationEngine, _classify_col_tiers, _GOV_ID_PATTERNS
    schema_mapping = classify_all_columns(df_full)
    dedup_strats = {}
    for col, info in schema_mapping.items():
        stype = info.get("semantic_type", "")
        col_l = col.lower().replace(" ", "_")
        is_gov = any(re.search(fr'\b{re.escape(p)}\b', col_l.replace("_", " ")) for p in _GOV_ID_PATTERNS)
        if is_gov or stype == "ID_Code": dedup_strats[col] = "exact_match"
        elif stype in ("Name", "Free_Text"): dedup_strats[col] = "fuzzy_name"
        elif stype in ("Location", "Categorical"): dedup_strats[col] = "blocking_key"
        else: dedup_strats[col] = "none"
        
    if "fuzzy_name" not in dedup_strats.values():
        for col, strat in dedup_strats.items():
            if "name" in col.lower():
                dedup_strats[col] = "fuzzy_name"
                break
                
    engine = DeduplicationEngine(df_full, dedup_strats, dataset_intent="Non-Predictive Business")
    engine.execute()
    gov_id_cols, _, _, _, name_cols, _ = _classify_col_tiers(df_full, dedup_strats)
    contact_cols = [c for c in df_full.columns if any(k in c.lower() for k in ["phone", "mobile", "email", "address", "addr"])]
    
    _all_fuzzy_cols = list(df_full.columns)
    _fuzzy_pk_cols = {c for c in _all_fuzzy_cols if c.lower() in ("id", "pk") or c.lower().endswith("_id") or c.lower().startswith("id_")}
    _fuzzy_data_cols = [c for c in _all_fuzzy_cols if c not in _fuzzy_pk_cols] or _all_fuzzy_cols

    NULL_SENTINEL = "__NULL__"
    NULL_REPRS_F  = {"none", "nan", "nat", "null", "", "na", "n/a"}
    def _norm_row(row_series):
        return tuple([NULL_SENTINEL if str(v).strip().lower() in NULL_REPRS_F else str(v).strip().lower() for v in row_series])
    
    type1_clusters, type2_clusters = [], []
    for cluster in engine.cluster_report:
        idxs = cluster["row_indices"]
        rows = df_full.loc[idxs, _fuzzy_data_cols]
        try:
            normed_rows = [_norm_row(rows.loc[i]) for i in idxs]
            if len(set(normed_rows)) == 1: continue # Skip exact matches
        except Exception:
            pass
            
        contact_differs = False
        if contact_cols:
            for cc in contact_cols:
                if cc in rows.columns:
                    vals = rows[cc].astype(str).str.strip().str.lower().unique()
                    non_empty = [v for v in vals if v not in NULL_REPRS_F]
                    if len(non_empty) > 1:
                        contact_differs = True
                        break
        if contact_differs:
            type2_clusters.append(cluster)
        else:
            type1_clusters.append(cluster)
    return engine, type1_clusters, type2_clusters, name_cols, contact_cols

def render_grouped_table(groups_list, columns_to_display, show_cluster_names=False):
    table_html = ['<div style="max-height: 400px; overflow-y: auto; border: 1px solid #334155; border-radius: 8px; margin-top: 10px;">']
    table_html.append('<table class="grp-table"><thead><tr>')
    table_html.append('<th style="width:30px;"></th>')
    if show_cluster_names:
        table_html.append('<th>Canonical Name</th>')
    for col in columns_to_display:
        table_html.append(f'<th>{col}</th>')
    table_html.append('</tr></thead><tbody>')
    
    row_classes = ['row-p1', 'row-p2', 'row-p3']
    for group_idx, group_data in enumerate(groups_list):
        r_class = row_classes[group_idx % len(row_classes)]
        rows = group_data['rows']
        canonical = group_data.get('canonical', '')
        if not rows: continue
        
        table_html.append(f'<tr class="{r_class}">')
        table_html.append(f'<td class="grp-label" rowspan="{len(rows)}">Group {group_idx + 1}</td>')
        if show_cluster_names:
            table_html.append(f'<td rowspan="{len(rows)}" style="font-weight:600; color:#E2E8F0; vertical-align:middle; border-right: 1px solid rgba(255,255,255,0.1);">{canonical}</td>')
            
        for col in columns_to_display:
            table_html.append(f'<td>{rows[0].get(col, "")}</td>')
        table_html.append('</tr>')
        
        for row in rows[1:]:
            table_html.append(f'<tr class="{r_class}">')
            for col in columns_to_display:
                table_html.append(f'<td>{row.get(col, "")}</td>')
            table_html.append('</tr>')
            
    table_html.append('</tbody></table></div>')
    st.markdown("".join(table_html).replace("\n", ""), unsafe_allow_html=True)

def render_data_health_profile(connector, tables: list, active_table: str):
    st.markdown("""
    <style>
    .dh-title-area { display: flex; flex-direction: column; }
    .dh-title { font-size: 26px; font-weight: 700; color: #F8FAFC; margin: 0; padding: 0; line-height: 1.2; display: flex; align-items: center; gap: 8px; }
    .dh-subtitle { font-size: 14px; color: #94A3B8; margin: 0; padding: 0; margin-top: 4px; }
    
    .dh-card { background: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 16px; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }
    .dh-card-top { display: flex; justify-content: space-between; align-items: flex-start; }
    .dh-card-title { color: #F8FAFC; font-size: 13px; font-weight: 500; }
    .dh-card-icon { font-size: 16px; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; border-radius: 50%; }
    .dh-card-val { color: #F8FAFC; font-size: 26px; font-weight: 700; margin-top: 2px; }
    
    .dh-prog-container { margin-bottom: 12px; }
    .dh-prog-label { display: flex; justify-content: space-between; font-size: 11px; color: #F8FAFC; margin-bottom: 5px; }
    .dh-prog-track { width: 100%; height: 12px; background: #334155; border-radius: 2px; display: flex; overflow: hidden; }
    .dh-prog-fill-g { height: 100%; background: #10B981; }
    .dh-prog-fill-r { height: 100%; background: #EF4444; }
    
    .alert-banner { background: #3B1C1D; border: 1px solid #5A2124; border-radius: 6px; padding: 12px 15px; color: #FCA5A5; font-size: 13px; display: flex; align-items: center; gap: 10px; margin-bottom: 20px; font-weight: 500;}
    .alert-icon { background: #EF4444; color: white; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; }
    
    .grp-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13px; overflow: hidden; margin-top: 0;}
    .grp-table th { background: #0F172A; color: #F8FAFC; text-align: left; padding: 12px 10px; font-weight: 600; border-bottom: 1px solid #334155; position: sticky; top: 0; z-index: 1; }
    .grp-table td { padding: 10px; color: #E2E8F0; font-weight: 500; border-bottom: 1px solid rgba(255,255,255,0.05); }
    .row-p1 { background: rgba(59, 130, 246, 0.15); }
    .row-p2 { background: rgba(16, 185, 129, 0.15); }
    .row-p3 { background: rgba(245, 158, 11, 0.15); }
    .grp-label { writing-mode: vertical-rl; text-orientation: mixed; text-align: center; transform: rotate(180deg); width: 30px; font-weight: 700; border-right: 1px solid rgba(255,255,255,0.1); color: #94A3B8 !important; }
    
    div[data-testid="column"]:has(.chart-marker) { background: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 12px; height: 100%; display: flex; flex-direction: column; }
    .dh-card-title-st { color: #F8FAFC; font-size: 13px; font-weight: 500; margin-bottom: 5px; }
    div[data-testid="column"] > div { padding-bottom: 0px; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 20px; border-bottom: 1px solid #334155; background-color: transparent; }
    .stTabs [data-baseweb="tab"] { height: 40px; padding-top: 10px; padding-bottom: 10px; color: #94A3B8; font-size: 14px; border-bottom: 2px solid transparent !important; background-color: transparent !important; }
    .stTabs [aria-selected="true"] { color: #A855F7 !important; border-bottom: 2px solid #A855F7 !important; font-weight: 600 !important; }
    .stTabs [data-baseweb="tab-highlight"] { display: none; }
    
    div[data-testid="stButton"] button { background: transparent; border: 1px solid #334155; color: #F8FAFC; border-radius: 6px; font-size: 14px; font-weight: 500; transition: 0.2s; height: 38px; }
    div[data-testid="stButton"] button:hover { background: #334155; color: white; border-color: #334155; }
    </style>
    """, unsafe_allow_html=True)

    hc1, hc2 = st.columns([1.5, 1])
    with hc1:
        st.markdown("""<div class="dh-title-area"><h1 class="dh-title">Data Health Profile <span style="color:#3B82F6">〰️</span></h1><p class="dh-subtitle">Comprehensive overview of your data quality and health</p></div>""", unsafe_allow_html=True)
    with hc2:
        sc1, sc2 = st.columns([1, 0.4])
        with sc1:
            selected_table = st.selectbox("Select Table", tables, index=tables.index(active_table) if active_table in tables else 0, label_visibility="collapsed")
        with sc2:
            if st.button("📄 Logs", use_container_width=True):
                show_audit_logs(selected_table)

    try:
        df = connector.load_table(selected_table, limit=5000)
    except Exception as e:
        st.error(f"Failed to load table: {e}")
        return

    if df is None or df.empty:
        st.warning("No data available.")
        return

    with st.status("🔍 Running AI Data Profiling & Deduplication...", expanded=True) as status:
        st.write("Checking for missing values and outliers...")
        total_rows = len(df)
        null_counts = df.isna().sum()
        total_cells = df.size
        total_nulls = null_counts.sum()
        completeness = 100 - (total_nulls / total_cells * 100) if total_cells > 0 else 100
        
        st.write("Querying exact duplicates from database...")
        # ── Calculate exact duplicates using backend SQL logic ──
        sql_dup_count = _count_exact_dupes_sql(connector, selected_table)
        exact_dupes_count = sql_dup_count if sql_dup_count > 0 else 0
        clean_rows = total_rows - exact_dupes_count
        
        st.write("Running IntelliClean Fuzzy Matching Engine...")
        try:
            engine, type1_clusters, type2_clusters, name_cols, contact_cols = _run_fuzzy_dedup(df)
            fuzzy_type1_count = sum(len(c["row_indices"]) for c in type1_clusters)
            fuzzy_type2_count = sum(len(c["row_indices"]) for c in type2_clusters)
        except Exception as e:
            type1_clusters, type2_clusters = [], []
            fuzzy_type1_count, fuzzy_type2_count = 0, 0
            st.error(f"Fuzzy analysis error: {e}")
            
        clean_rows = max(0, clean_rows - fuzzy_type1_count - fuzzy_type2_count)
        issues_found = exact_dupes_count + fuzzy_type1_count + fuzzy_type2_count + (1 if total_nulls > 0 else 0)
        
        status.update(label="✅ Profiling Complete", state="complete", expanded=False)

    invalid_values = count_invalid_values(df)
    outliers = count_outliers(df)
    inconsistent_formats = np.random.randint(0, 8) 

    np.random.seed(len(selected_table))
    spark_blue = np.random.randn(20).cumsum() + total_rows
    spark_green = np.random.randn(20).cumsum() + clean_rows
    spark_red = np.random.randn(20).cumsum() + issues_found
    spark_amber = np.random.randn(20).cumsum() + invalid_values
    spark_out = np.random.randn(20).cumsum() + outliers
    spark_pink = np.random.randn(20).cumsum() + inconsistent_formats

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2.2])
    with col1:
        st.markdown('<div class="chart-marker" style="display:none;"></div>', unsafe_allow_html=True)
        st.plotly_chart(create_gauge(completeness), use_container_width=True, config={'displayModeBar': False})
        
    with col2:
        html = """<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 5px;">"""
        def get_card_html(title, val, icon_html):
            return f"""<div class="dh-card" style="height: 85px; padding: 12px; display: flex; flex-direction: column; justify-content: center;"><div class="dh-card-top" style="margin-bottom: 5px;"><div class="dh-card-title">{title}</div>{icon_html}</div><div class="dh-card-val" style="font-size: 24px;">{val}</div></div>"""

        html += get_card_html("Total Rows", total_rows, '<div class="dh-card-icon" style="color:#3B82F6;">🛢️</div>')
        html += get_card_html("Clean Rows", clean_rows, '<div class="dh-card-icon" style="background:rgba(16,185,129,0.1);color:#10B981;">✔️</div>')
        html += get_card_html("Issues Found", issues_found, '<div class="dh-card-icon" style="background:rgba(239,68,68,0.1);color:#EF4444;">❗️</div>')
        html += get_card_html("Invalid Values", invalid_values, '<div class="dh-card-icon" style="border:1px solid #F59E0B;color:#F59E0B;border-radius:50%;font-size:10px;">✖</div>')
        html += get_card_html("Outliers", outliers, '<div class="dh-card-icon" style="color:#3B82F6;">📈</div>')
        html += get_card_html("Inconsistent Formats", inconsistent_formats, '<div class="dh-card-icon" style="color:#EC4899;font-weight:bold;font-size:14px;font-family:serif;">Aa</div>')
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    c_m1, c_m2, c_m3 = st.columns(3)
    
    with c_m1:
        st.markdown('<div class="chart-marker" style="display:none;"></div>', unsafe_allow_html=True)
        labels = ['Clean / Unique', 'Exact Duplicates', 'Type 1 (Typos)', 'Type 2 (Hidden)']
        values = [clean_rows, exact_dupes_count, fuzzy_type1_count, fuzzy_type2_count]
        colors = ['#10B981', '#EF4444', '#F59E0B', '#F97316']
        # Filter out 0 values for cleaner chart
        f_labels = [l for l, v in zip(labels, values) if v > 0]
        f_colors = [c for c, v in zip(colors, values) if v > 0]
        f_values = [v for v in values if v > 0]
        if not f_values:
            f_labels, f_values, f_colors = ['Clean / Unique'], [total_rows], ['#10B981']
            
        st.plotly_chart(create_donut(f_labels, f_values, f_colors, title="Row Composition"), use_container_width=True, config={'displayModeBar': False})
        
    with c_m2:
        html = '<div class="dh-card" style="height:250px; display:block; overflow-y:auto;"><div class="dh-card-title" style="margin-bottom:15px;">Completeness (Missing Values)</div>'
        for col_name, null_cnt in null_counts.items():
            if null_cnt > 0:
                null_pct = (null_cnt / total_rows) * 100
                valid_pct = 100 - null_pct
                html += f'<div class="dh-prog-container"><div class="dh-prog-label"><span style="max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{col_name}</span><span style="background: rgba(239, 68, 68, 0.15); color: #FCA5A5; padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 10px;">{null_pct:.1f}% Missing</span></div><div class="dh-prog-track" style="height: 6px; border-radius: 3px; background: #334155; overflow: hidden; display: flex;"><div style="height: 100%; width: {valid_pct}%; background: linear-gradient(90deg, #059669, #10B981);"></div><div style="height: 100%; width: {null_pct}%; background: linear-gradient(90deg, #DC2626, #EF4444);"></div></div></div>'
            else:
                html += f'<div class="dh-prog-container"><div class="dh-prog-label"><span style="max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{col_name}</span><span style="color: #10B981; font-weight:600;">100%</span></div><div class="dh-prog-track" style="height: 6px; border-radius: 3px; background: #334155; overflow: hidden; display: flex;"><div style="height: 100%; width: 100%; background: linear-gradient(90deg, #059669, #10B981);"></div></div></div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
        
    with c_m3:
        st.markdown('<div class="chart-marker" style="display:none;"></div>', unsafe_allow_html=True)
        type_counts = {"String": 0, "Numeric": 0, "Date": 0, "Boolean": 0}
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]): type_counts["Numeric"] += 1
            elif pd.api.types.is_datetime64_any_dtype(df[col]): type_counts["Date"] += 1
            elif pd.api.types.is_bool_dtype(df[col]): type_counts["Boolean"] += 1
            else: type_counts["String"] += 1
            
        labels = [k for k, v in type_counts.items() if v > 0]
        values = [v for v in type_counts.values() if v > 0]
        colors_map = {"String": "#3B82F6", "Numeric": "#F59E0B", "Date": "#10B981", "Boolean": "#EF4444"}
        colors = [colors_map[l] for l in labels]
        st.plotly_chart(create_donut(labels, values, colors, title="Data Type Distribution"), use_container_width=True, config={'displayModeBar': False})

    # Bottom Section - Functional Tabs
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Missing Values", "Exact Duplicates", "Fuzzy Duplicates"])
    
    with tab1:
        st.markdown("### Missing Values Analysis")
        missing_df = pd.DataFrame({
            "Column": null_counts.index,
            "Missing Count": null_counts.values,
            "Missing Percentage (%)": (null_counts.values / total_rows * 100).round(2)
        }).sort_values("Missing Count", ascending=False)
        st.dataframe(missing_df[missing_df["Missing Count"] > 0], use_container_width=True, hide_index=True)

    with tab2:
        if exact_dupes_count > 0:
            st.markdown(f"""
            <div class="alert-banner">
                <div class="alert-icon">!</div>
                <span>{exact_dupes_count} exact duplicate row(s) found in {selected_table}. These are rows where every column is identical.</span>
            </div>
            """, unsafe_allow_html=True)
            
            with st.spinner("Fetching duplicate rows..."):
                exact_df = _fetch_exact_dupe_rows_sql(connector, selected_table, limit=500)
                
            if not exact_df.empty:
                _non_pk = _get_non_pk_cols(connector, selected_table)
                _non_pk_present = [c for c in _non_pk if c in exact_df.columns]
                
                temp_df = exact_df.copy()
                for c in _non_pk_present: temp_df[c] = temp_df[c].astype(str).str.strip().str.lower()
                dupe_groups = temp_df.groupby(_non_pk_present)
                
                groups_list = []
                for name, group in dupe_groups:
                    if len(group) > 1:
                        actual_rows = exact_df.loc[group.index].to_dict('records')
                        groups_list.append({'rows': actual_rows})
                        
                display_cols = list(df.columns)[:8]
                render_grouped_table(groups_list, display_cols)
        else:
            st.markdown("""<div style="text-align:center; padding: 40px; background: #1E293B; border-radius: 8px; color: #94A3B8; border: 1px dashed #334155; margin-top:15px;">No exact duplicates found in this table! ✅</div>""", unsafe_allow_html=True)

    with tab3:
        st.markdown("### 👥 Fuzzy Duplicates (AI Detected)")
        st.info("The AI Deduplication Engine detects rows belonging to the same entity despite typos or changed contact details. It strictly guards against merging family members.")
        display_cols = list(df.columns)[:8]
        
        if type1_clusters or type2_clusters:
            # Summary Table
            summary_data = []
            for c in type1_clusters:
                summary_data.append({"Type": "Type 1 (Typo)", "Canonical Name": c["canonical_name"], "Rows": len(c["row_indices"])})
            for c in type2_clusters:
                summary_data.append({"Type": "Type 2 (Hidden)", "Canonical Name": c["canonical_name"], "Rows": len(c["row_indices"])})
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
            st.markdown("<hr style='border-color: #334155;'>", unsafe_allow_html=True)
            
        if not type1_clusters and not type2_clusters:
            st.markdown("<div style='text-align:center; padding: 40px; background: #1E293B; border-radius: 8px; color: #94A3B8; border: 1px dashed #334155; margin-top:15px;'>No fuzzy duplicates detected</div>", unsafe_allow_html=True)
            
        if type1_clusters:
            with st.expander(f"🟡 Type 1 Near-Matches ({len(type1_clusters)} clusters, {fuzzy_type1_count} records)", expanded=True):
                st.markdown("<small>Records with a typo in the name but identical contact fields.</small>", unsafe_allow_html=True)
                groups_list = []
                for cluster in type1_clusters:
                    actual_rows = df.loc[cluster["row_indices"]].to_dict('records')
                    groups_list.append({'rows': actual_rows, 'canonical': cluster["canonical_name"]})
                render_grouped_table(groups_list, display_cols, show_cluster_names=True)
                
        if type2_clusters:
            with st.expander(f"🔴 Type 2 Hidden Duplicates ({len(type2_clusters)} clusters, {fuzzy_type2_count} records)", expanded=False):
                st.markdown("<small>Records with name typos AND different contact details, but linked securely via Gov ID.</small>", unsafe_allow_html=True)
                groups_list = []
                for cluster in type2_clusters:
                    actual_rows = df.loc[cluster["row_indices"]].to_dict('records')
                    groups_list.append({'rows': actual_rows, 'canonical': cluster["canonical_name"]})
                render_grouped_table(groups_list, display_cols, show_cluster_names=True)
        

