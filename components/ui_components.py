import html
import pandas as pd
from backend.exporter import Exporter

def render_cleaning_results(st, cleaned_df, metadata, logs=None):
    if logs is None:
        logs = []

    # -- SUCCESS BANNER --
    st.markdown(f"""
    <div class="glass-panel success" style="display:flex;align-items:center;gap:16px;margin-top:1.5rem">
      <div style="font-size:2rem">&#10024;</div>
      <div>
        <div style="font-weight:700;color:#4ade80;font-size:1rem">IntelliClean Pipeline Execution Complete</div>
        <div style="font-size:0.78rem;color:#64748b;margin-top:2px">
          Processed in {metadata.get('execution_time_sec', 0.0):.1f}s &nbsp;&middot;&nbsp;
          {metadata.get('initial_rows', len(cleaned_df))} rows in &nbsp;&rarr;&nbsp; {metadata.get('final_rows', len(cleaned_df))} rows out
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # -- METRICS ROW --
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
        <div class="metric-value">{metadata.get('initial_rows', len(cleaned_df)):,}</div>
        <div class="metric-sub">Input dataset size</div>
      </div>
      <div class="metric-card cyan">
        <div class="metric-label">Cleaned Rows</div>
        <div class="metric-value">{metadata.get('final_rows', len(cleaned_df)):,}</div>
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
        <div class="metric-sub">{domain_conf} confidence &middot; {domain_method}</div>
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

    # -- TABBED RESULTS --
    tab_preview, tab_schema, tab_ml, tab_impute, tab_dedup, tab_currency, tab_audit = st.tabs([
        "📊 Cleaned Data",
        "🧠 Schema Analysis",
        "🌐 Multilingual",
        "🧩 Imputation",
        "🔗 Deduplication",
        "💱 Currency",
        "📋 Audit Trail",
    ])

    # - Tab 1: Cleaned Preview -
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

    # - Tab 2: Schema -
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
                    "Multilingual": "&#10003; Yes" if info.get("needs_multilingual") else "&mdash; No",
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
                "Numeric": "tag-pink", "Temporal": "tag-gray",
                "ID_Code": "tag-gray", "Free_Text": "tag-gray", "Location": "tag-cyan",
            }
            for t, c in type_counts.items():
                color = color_map.get(t, "tag-gray")
                chips_html += f'<span class="tag {color}">{t}: {c}</span> '
            st.markdown(chips_html, unsafe_allow_html=True)
        else:
            st.info("No schema information available.")

    # - Tab 3: Multilingual -
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
                        change_rows = [{"Original": k, "&rarr; Cleaned": v} for k, v in list(changes.items())[:50]]
                        st.dataframe(pd.DataFrame(change_rows), use_container_width=True, height=250)
        else:
            st.markdown("""
            <div class="glass-panel">
              <div style="color:#64748b;font-size:0.85rem">No multilingual processing was required &mdash; all values were already in English.</div>
            </div>
            """, unsafe_allow_html=True)

    # - Tab 4: Imputation -
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
                    &rarr; fill <code style="background:rgba(74,222,128,0.12);padding:1px 5px;border-radius:4px;color:#4ade80">'{r.get('fill_value','?')}'</code>
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
                    extra_html = f"""<div style="display:flex;flex-wrap:wrap;gap:1.5rem;font-size:0.75rem;color:#64748b;margin-top:6px;background:rgba(0,0,0,0.2);padding:8px 10px;border-radius:6px;line-height:1.4"><div><b style="color:#94a3b8">Mean:</b> {mean}</div><div><b style="color:#94a3b8">Median:</b> {median}</div><div><b style="color:#94a3b8">Skewness:</b> {skew}</div><div><b style="color:#94a3b8">Range:</b> {min_val} to {max_val}</div></div>"""
                elif strategy == "fill_mode":
                    unique = s.get('unique_vals', '?')
                    top_dist = s.get('top_distribution', {})
                    dist_str = " &middot; ".join([f"{k}: {v}" for k, v in top_dist.items()])
                    extra_html = f"""<div style="display:flex;flex-wrap:wrap;gap:1.5rem;font-size:0.75rem;color:#64748b;margin-top:6px;background:rgba(0,0,0,0.2);padding:8px 10px;border-radius:6px;line-height:1.4"><div><b style="color:#94a3b8">Unique Values:</b> {unique}</div><div style="flex:1;min-width:200px;word-break:break-word"><b style="color:#94a3b8">Top Distribution:</b> {dist_str}</div></div>"""

                # Get AI Reasoning for this column
                schema_mapping = metadata.get("schema_mapping", {})
                col_schema = schema_mapping.get(col, {})
                ai_reasoning = col_schema.get("imputation_reasoning", "")
                
                reasoning_html = ""
                if ai_reasoning:
                    reasoning_html = f"""<div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.05);display:flex;align-items:center;gap:8px"><span style="font-size:0.9rem">🤖</span><span style="font-size:0.78rem;color:#a78bfa"><b>AI Reasoning:</b> {ai_reasoning}</span></div>"""

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
                  <div style="color:#4ade80;font-weight:600;margin-bottom:4px">&#10003; No Imputation Needed</div>
                  <div style="color:#64748b;font-size:0.82rem">Any missing values were successfully resolved during earlier phases.</div>
                </div>
                """, unsafe_allow_html=True)

    # - Tab 5: Deduplication -
    with tab_dedup:
        st.markdown('<div class="section-header">🔗 <span>Entity Consolidation &amp; Deduplication</span></div>', unsafe_allow_html=True)
        changes = metadata.get("dedup_changes", [])
        cluster_report = metadata.get("dedup_cluster_report", [])

        # Summary banner
        total_clusters = len(cluster_report)
        total_merged = sum(c.get("cluster_size", 1) - 1 for c in cluster_report)

        if total_clusters > 0:
            st.markdown(f"""
            <div class="glass-panel" style="display:flex;align-items:center;gap:1.5rem;padding:1rem 1.2rem;margin-bottom:1rem">
              <div style="font-size:2rem">&#128269;</div>
              <div>
                <div style="font-weight:700;color:#a78bfa;font-size:1rem">{total_clusters} Duplicate Cluster(s) Detected</div>
                <div style="font-size:0.8rem;color:#64748b;margin-top:2px">
                  {total_merged} duplicate row(s) collapsed &nbsp;&middot;&nbsp;
                  <span class="tag tag-purple">{len(changes)} unique entities consolidated</span>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        
        if changes:
            # Deduplicate any exact dict copies if they exist
            seen = set()
            unique_changes = []
            for c in changes:
                key = (c.get("Original"), c.get("Corrected"))
                if key not in seen:
                    seen.add(key)
                    unique_changes.append(c)

            st.markdown("<br>", unsafe_allow_html=True)

            for c in unique_changes:
                orig = html.escape(str(c.get("Original", "?")))
                corr = html.escape(str(c.get("Corrected", "?")))
                size = c.get("cluster_size", 1)
                reasons_dict = c.get("reasons", {})
                all_variants = c.get("all_variants", [])

                # Build reason badges
                reasons_html = ""
                for r_name, r_count in reasons_dict.items():
                    badge_color = "#3b82f6"
                    r_name_esc = html.escape(str(r_name))
                    if "Fuzzy" in r_name:
                        badge_color = "#a855f7"
                    elif "Exact" in r_name:
                        badge_color = "#10b981"
                    elif "Composite" in r_name or "Partial" in r_name or "Multifield" in r_name:
                        badge_color = "#f59e0b"
                    elif "Gov" in r_name:
                        badge_color = "#22d3ee"
                    reasons_html += f'<span class="tag" style="background:{badge_color}33;color:{badge_color};margin-right:6px">{r_count}x {r_name_esc}</span>'

                if not reasons_html:
                    reasons_html = '<span class="tag tag-cyan">Exact Duplicate</span>'

                # Show variant names
                variants_html = ""
                if all_variants:
                    variant_names = [html.escape(v.get("name", "")) for v in all_variants if v.get("name")]
                    if variant_names:
                        # Pre-compute the joined codes BEFORE the triple-quoted f-string
                        # to avoid nested f-string quote conflicts (Python 3.12+ PEP 701 issue)
                        variant_codes = "  &rarr;  ".join(
                            '<code style="background:rgba(248,113,113,0.1);color:#f87171;padding:1px 5px;border-radius:4px">'
                            + n + "</code>"
                            for n in variant_names[:5]
                        )
                        more_indicator = "..." if len(variant_names) > 5 else ""
                        variants_html = (
                            '<div style="margin-top:8px;font-size:0.75rem;color:#64748b">'
                            '<span style="color:#64748b;text-transform:uppercase;letter-spacing:0.5px;font-size:0.65rem">Original Variants: </span>'
                            + variant_codes + more_indicator +
                            "</div>"
                        )

                st.markdown(f"""
                <div class="glass-panel" style="margin-bottom:0.8rem;padding:1rem">
                  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                    <div style="font-size:0.95rem;font-weight:600;color:#e2e8f0">{corr}</div>
                    <div style="font-size:0.75rem;color:#94a3b8">Merged <b style="color:#e2e8f0">{size - 1}</b> duplicate(s) into 1 record</div>
                  </div>

                  <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;font-size:0.85rem">
                    <span style="color:#f43f5e;text-decoration:line-through">{orig}</span>
                    <span style="color:#64748b">&rarr;</span>
                    <span style="color:#22d3ee">{corr}</span>
                  </div>
                  {variants_html}

                  <div style="padding-top:10px;border-top:1px solid rgba(255,255,255,0.05);">
                    <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:#64748b;margin-bottom:6px;">Merge Reason(s)</div>
                    {reasons_html}
                  </div>
                </div>
                """, unsafe_allow_html=True)
        elif total_clusters == 0:
            st.markdown("""
            <div class="glass-panel success">
              <div style="color:#4ade80;font-weight:600;margin-bottom:4px">&#10003; No duplicates detected</div>
              <div style="color:#64748b;font-size:0.82rem">All records in your dataset appear to be unique entities.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Clusters were found but changes list is empty (edge case)
            st.info(f"{total_clusters} cluster(s) found. Exact duplicate rows were removed (no name variations to display).")

        # Validation issues
        issues = validation.get("issues", [])
        st.markdown('<div class="section-header" style="margin-top:1.5rem">&#128737; <span>Validation Results</span></div>', unsafe_allow_html=True)
        if issues:
            for issue in issues:
                issue_esc = html.escape(str(issue))
                st.markdown(f"""
                <div class="glass-panel warning">
                  <div style="font-size:0.83rem;color:#fbbf24">&#9888; {issue_esc}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="glass-panel success">
              <div style="color:#4ade80;font-weight:600">&#10003; No validation issues found</div>
              <div style="color:#64748b;font-size:0.82rem">Cleaned dataset passed all post-cleaning quality checks.</div>
            </div>
            """, unsafe_allow_html=True)

    # - Tab 6: Currency Conversion -
    with tab_currency:
        st.markdown('<div class="section-header">💱 <span>Currency Detection & Conversion</span></div>', unsafe_allow_html=True)
        currency_report = metadata.get("currency_report", [])
        if currency_report:
            st.markdown(f"""
            <div class="glass-panel success" style="display:flex;align-items:center;gap:14px;padding:0.9rem 1.2rem">
              <div style="font-size:1.8rem">&#8377;</div>
              <div>
                <div style="font-weight:700;color:#4ade80;font-size:0.95rem">Currency Conversion Complete</div>
                <div style="font-size:0.78rem;color:#64748b;margin-top:2px">
                  {len(currency_report)} column(s) detected with mixed currencies &nbsp;&middot;&nbsp; All values converted to <b style="color:#4ade80">INR (&#8377;)</b>
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
                    f'<div><b style="color:#94a3b8">1 {c}</b> = <span style="color:#4ade80">&#8377;{r:,.4f}</span></div>'
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
                    <div>&#10003; <b style="color:#4ade80">{converted}</b> rows converted</div>
                    <div>&#128993; <b style="color:#fbbf24">{assumed}</b> rows assumed INR (no symbol)</div>
                    <div>{'&#10060; <b style="color:#f87171">' + str(failed) + '</b> rows unparseable' if failed else ''}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="glass-panel success">
              <div style="color:#4ade80;font-weight:600;margin-bottom:4px">&#10003; No currency conversion needed</div>
              <div style="color:#64748b;font-size:0.82rem">No columns with mixed foreign currencies were detected in your dataset.</div>
            </div>
            """, unsafe_allow_html=True)

    # - Tab 7: Audit Trail -
    with tab_audit:
        st.markdown('<div class="section-header">&#128203; <span>AI Audit Trail</span></div>', unsafe_allow_html=True)
        explanations = metadata.get("explanations", [])

        _SEVERITY_COLORS = {
            "info":    ("#22d3ee",  "rgba(34,211,238,0.07)",  "rgba(34,211,238,0.25)"),
            "change":  ("#a78bfa",  "rgba(139,92,246,0.07)",  "rgba(139,92,246,0.3)"),
            "warning": ("#fbbf24",  "rgba(251,191,36,0.07)",  "rgba(251,191,36,0.3)"),
            "fix":     ("#4ade80",  "rgba(74,222,128,0.06)",  "rgba(74,222,128,0.25)"),
            "remove":  ("#f87171",  "rgba(248,113,113,0.06)", "rgba(248,113,113,0.25)"),
            "detect":  ("#60a5fa",  "rgba(96,165,250,0.07)",  "rgba(96,165,250,0.25)"),
            "llm":     ("#c084fc",  "rgba(192,132,252,0.07)", "rgba(192,132,252,0.3)"),
            "error":   ("#f43f5e",  "rgba(244,63,94,0.07)",   "rgba(244,63,94,0.3)"),
        }

        if explanations:
            # Check if new rich format (has 'step' key) or old flat format
            is_rich = any("step" in e for e in explanations)
            html_parts = []

            if is_rich:
                # ── Group by pipeline step ──────────────────────────────
                from collections import defaultdict
                steps_map = defaultdict(list)
                for exp in explanations:
                    step_key = f"{exp.get('step_number', 99):02d}_{exp.get('step', 'Other')}"
                    steps_map[step_key].append(exp)

                step_icons = {
                    "Domain Detection":      "🔍",
                    "Schema Classification": "🧠",
                    "Multilingual Processing": "🌐",
                    "String Pre-cleaning":   "✨",
                    "Entity Resolution":     "👥",
                    "Deduplication":         "🗑️",
                    "Smart Imputation":      "🧩",
                    "Outlier Handling":      "📊",
                    "Currency Conversion":   "💱",
                    "Validation":            "✅",
                    "Pipeline Complete":     "🏁",
                }

                for step_key in sorted(steps_map.keys()):
                    step_entries = steps_map[step_key]
                    step_name   = step_entries[0].get("step", "Other")
                    step_num    = step_entries[0].get("step_number", "?")
                    step_icon   = step_icons.get(step_name, "⚙️")

                    # Count meaningful changes in this step
                    n_changes = sum(1 for e in step_entries if e.get("severity") in ("change", "fix", "remove"))
                    badge_html = (
                        f'<span style="background:rgba(139,92,246,0.15);color:#a78bfa;'
                        f'border:1px solid rgba(139,92,246,0.3);border-radius:6px;'
                        f'padding:2px 8px;font-size:0.7rem;font-weight:700">'
                        f'{n_changes} change(s)</span>' if n_changes > 0 else
                        '<span style="background:rgba(100,116,139,0.15);color:#64748b;'
                        'border:1px solid rgba(100,116,139,0.2);border-radius:6px;'
                        'padding:2px 8px;font-size:0.7rem">no changes</span>'
                    )

                    html_parts.append(
                        f'<div style="display:flex;align-items:center;gap:10px;'
                        f'font-size:0.9rem;font-weight:700;color:#e2e8f0;'
                        f'border-bottom:1px solid rgba(255,255,255,0.07);'
                        f'padding-bottom:0.5rem;margin:1.4rem 0 0.8rem">'
                        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
                        f'width:24px;height:24px;border-radius:50%;background:rgba(139,92,246,0.2);'
                        f'border:1px solid rgba(139,92,246,0.4);font-size:0.7rem;font-weight:700;'
                        f'color:#a78bfa">{step_num}</span>'
                        f'{step_icon} {step_name} {badge_html}</div>'
                    )

                    for exp in step_entries:
                        severity = exp.get("severity", "info")
                        icon     = exp.get("icon", "ℹ️")
                        col_name = html.escape(str(exp.get("column", "")))
                        task     = html.escape(str(exp.get("task", "")))
                        original = html.escape(str(exp.get("original", "")))
                        cleaned  = html.escape(str(exp.get("cleaned", "")))
                        expl     = html.escape(str(exp.get("explanation", "")))

                        text_color, bg_color, border_color = _SEVERITY_COLORS.get(
                            severity, ("#94a3b8", "rgba(255,255,255,0.03)", "rgba(255,255,255,0.07)")
                        )

                        # Build original → cleaned arrow if both present
                        arrow_html = ""
                        if original and cleaned:
                            arrow_html = (
                                f'<div style="display:flex;align-items:center;gap:8px;'
                                f'font-size:0.78rem;margin-bottom:5px">'
                                f'<code style="background:rgba(248,113,113,0.1);color:#f87171;'
                                f'padding:1px 6px;border-radius:4px;white-space:nowrap">'
                                f'{original}</code>'
                                f'<span style="color:#475569">&#8594;</span>'
                                f'<code style="background:rgba(74,222,128,0.1);color:#4ade80;'
                                f'padding:1px 6px;border-radius:4px;white-space:nowrap">'
                                f'{cleaned}</code>'
                                f'</div>'
                            ) if original != cleaned else (
                                f'<div style="font-size:0.78rem;color:#64748b;margin-bottom:4px">'
                                f'<code style="background:rgba(100,116,139,0.1);color:#94a3b8;'
                                f'padding:1px 6px;border-radius:4px">{cleaned}</code></div>'
                            )

                        col_tag = (
                            f'<span style="background:rgba(139,92,246,0.12);color:#c4b5fd;'
                            f'border:1px solid rgba(139,92,246,0.25);border-radius:4px;'
                            f'padding:1px 7px;font-size:0.68rem;font-weight:600;'
                            f'font-family:monospace">{col_name}</span> ' if col_name and col_name != "DATASET" else
                            '<span style="background:rgba(34,211,238,0.08);color:#67e8f9;'
                            'border:1px solid rgba(34,211,238,0.2);border-radius:4px;'
                            'padding:1px 7px;font-size:0.68rem;font-weight:600">DATASET</span> '
                        )

                        html_parts.append(
                            f'<div style="background:{bg_color};border:1px solid {border_color};'
                            f'border-left:3px solid {text_color};border-radius:10px;'
                            f'padding:0.7rem 1rem;margin-bottom:0.45rem">'
                            f'  <div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">'
                            f'    <span style="font-size:1rem">{icon}</span>'
                            f'    {col_tag}'
                            f'    <span style="font-size:0.72rem;color:{text_color};'
                            f'background:{bg_color};border:1px solid {border_color};'
                            f'border-radius:4px;padding:1px 6px">{task}</span>'
                            f'  </div>'
                            f'  {arrow_html}'
                            f'  <div style="font-size:0.78rem;color:#94a3b8;line-height:1.6">'
                            f'    {expl}'
                            f'  </div>'
                            f'</div>'
                        )

            else:
                # ── Legacy flat format (backward compat) ────────────────
                for exp in explanations[:40]:
                    task = exp.get("task", "Transform")
                    task_color = "tag-purple" if "Translit" in task else "tag-cyan"
                    orig_esc    = html.escape(str(exp.get("original", "?")))
                    cleaned_esc = html.escape(str(exp.get("cleaned", "?")))
                    col_esc     = html.escape(str(exp.get("column", "?")))
                    expl_esc    = html.escape(str(exp.get("explanation", "")))
                    task_esc    = html.escape(str(task))
                    parts = [
                        '<div class="glass-panel" style="margin-bottom:0.5rem">',
                        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">',
                        '<span style="font-weight:600;color:#a78bfa;font-size:0.83rem">' + col_esc + '</span>',
                        '<span class="' + task_color + '" style="font-size:0.68rem">' + task_esc + '</span>',
                        '</div>',
                        '<div style="font-size:0.8rem;color:#64748b">',
                        '<code style="background:rgba(248,113,113,0.1);color:#f87171;padding:1px 5px;border-radius:4px">' + orig_esc + '</code>',
                        ' &rarr; ',
                        '<code style="background:rgba(74,222,128,0.1);color:#4ade80;padding:1px 5px;border-radius:4px">' + cleaned_esc + '</code>',
                        '</div>',
                        '<div style="font-size:0.75rem;color:#475569;margin-top:4px">&#128172; ' + expl_esc + '</div>',
                        '</div>',
                    ]
                    html_parts.append("".join(parts))

            # Helper to open full window report
            def show_full_report():
                now = __import__("datetime").datetime.now()
                date_str = now.strftime("%A, %d %B %Y")
                time_str = now.strftime("%I:%M %p")
                
                # Check for dialog support
                if hasattr(st, "dialog"):
                    dialog_dec = st.dialog("Detailed Audit & Changes Report", width="large")
                else:
                    def dialog_dec(f): return f
                
                @dialog_dec
                def _dialog():
                    st.markdown(f"### 📄 Comprehensive Change Report")
                    st.markdown(f"**Date:** {date_str} &nbsp;&middot;&nbsp; **Time:** {time_str}")
                    st.markdown("---")
                    
                    # Render all changes without fixed height restriction
                    st.markdown(
                        '<div style="background:#090d16; border:1px solid #1e293b; border-radius:10px; padding:1.2rem; box-shadow:inset 0 2px 8px rgba(0,0,0,0.5);">' +
                        "".join(html_parts) + '</div>',
                        unsafe_allow_html=True
                    )
                    
                    st.markdown("---")
                    col1, col2 = st.columns([1, 5])
                    with col1:
                        if st.button("Close Window", use_container_width=True):
                            st.rerun()
                
                _dialog()

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📄 View Full Changes Report (Full Window)", type="primary"):
                show_full_report()

        else:
            st.markdown("""
            <div class="glass-panel">
              <div style="color:#64748b;font-size:0.85rem">No transformation audit trail was generated for this run.</div>
            </div>
            """, unsafe_allow_html=True)

        # Execution log - HTML-escape to prevent tags from breaking the layout
        st.markdown('<div class="section-header" style="margin-top:1.5rem">&#128221; <span>Execution Log</span></div>', unsafe_allow_html=True)

        # Color-coded log rendering
        log_lines = []
        for line in logs:
            safe = html.escape(line)
            if any(k in line for k in ["Error", "Failed", "❌"]):
                log_lines.append(f'<span style="color:#f87171">{safe}</span>')
            elif "[Step" in line and "]" in line:
                log_lines.append(f'<span style="color:#a78bfa;font-weight:700">{safe}</span>')
            elif any(k in line for k in ["Completed", "✓", "Done", "PASSED", "✅"]):
                log_lines.append(f'<span style="color:#4ade80">{safe}</span>')
            elif any(k in line for k in ["[Domain", "[Schema", "[Imputation", "[Dedup", "[Outlier", "[Currency"]):
                log_lines.append(f'<span style="color:#22d3ee">{safe}</span>')
            elif any(k in line for k in ["LLM", "🤖", "AI ", "[Pass"]):
                log_lines.append(f'<span style="color:#c084fc">{safe}</span>')
            elif any(k in line for k in ["[WARNING]", "Warning", "⚠️"]):
                log_lines.append(f'<span style="color:#fbbf24">{safe}</span>')
            elif line.startswith("  ") and ":" in line:
                log_lines.append(f'<span style="color:#94a3b8">{safe}</span>')
            else:
                log_lines.append(f'<span style="color:#64748b">{safe}</span>')

        # Helper to open full execution log dialog
        def show_full_execution_log():
            now = __import__("datetime").datetime.now()
            date_str = now.strftime("%A, %d %B %Y")
            time_str = now.strftime("%I:%M %p")
            
            if hasattr(st, "dialog"):
                log_dialog_dec = st.dialog("Full Execution Log", width="large")
            else:
                def log_dialog_dec(f): return f
            
            @log_dialog_dec
            def _log_dialog():
                st.markdown(f"### 📝 Full Pipeline Execution Log")
                st.markdown(f"**Date:** {date_str} &nbsp;&middot;&nbsp; **Time:** {time_str}")
                st.markdown("---")
                
                st.markdown(
                    '<div style="background:#090d16; border:1px solid #1e293b; border-radius:10px; padding:1.2rem; font-family:\'Courier New\', monospace; font-size:0.8rem; color:#94a3b8; line-height:1.6; white-space:pre-wrap; box-shadow:inset 0 2px 8px rgba(0,0,0,0.5); display:block !important;">' +
                    "<br>".join(log_lines) + '</div>',
                    unsafe_allow_html=True
                )
                
                st.markdown("---")
                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.button("Close Window", key="close_log_dialog", use_container_width=True):
                        st.rerun()
            
            _log_dialog()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📝 View Full Execution Log (Full Window)", type="secondary"):
            show_full_execution_log()
