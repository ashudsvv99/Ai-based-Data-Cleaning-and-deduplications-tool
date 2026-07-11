"""
Explanation Agent — Rich Structured Audit Trail Generator.

Generates human-readable, structured explanations for ALL cleaning operations:
  - Domain detection reasoning
  - Schema classification (per column, with LLM reasoning)
  - Multilingual translation & transliteration
  - String pre-cleaning (whitespace, unicode, email, phone, dates)
  - Smart imputation (LLM contextual rules + statistical fallback)
  - Entity resolution (fuzzy name clustering)
  - Deduplication (exact + fuzzy, with merge reasons)
  - Outlier handling (per column, with stats)
  - Currency conversion (symbols + rates)
  - Validation issues
  - Pipeline timing summary

Output format:
  Each explanation entry has:
    {
      "step":        str   # Pipeline step name (e.g. "Domain Detection")
      "step_number": int   # 1-12
      "column":      str   # Column name (or "DATASET" for dataset-level ops)
      "task":        str   # Operation type (e.g. "Transliteration", "Imputation")
      "original":    str   # Before value or state (optional)
      "cleaned":     str   # After value or action taken
      "explanation": str   # Human-readable explanation
      "severity":    str   # "info" | "change" | "warning" | "fix"
      "icon":        str   # Emoji icon for the event type
    }
"""
import json
from typing import Dict, List, Optional
from agents.llm_client import LMStudioClient


# ── Severity → icon mapping ──────────────────────────────────
_SEVERITY_ICONS = {
    "info":    "ℹ️",
    "change":  "🔄",
    "warning": "⚠️",
    "fix":     "✅",
    "remove":  "🗑️",
    "detect":  "🔍",
    "llm":     "🤖",
    "error":   "❌",
}


class ExplanationAgent:
    """
    Generates natural language explanations for each cleaning transformation,
    creating a comprehensive human-readable audit trail across all 12 pipeline steps.
    """

    def __init__(self, llm_client: LMStudioClient = None):
        self.llm_client = llm_client or LMStudioClient()

    # ─────────────────────────────────────────────────────────────
    # Main entry point — called by PipelineOrchestrator at Step 12
    # ─────────────────────────────────────────────────────────────
    def explain_transformations(
        self,
        translation_stats: dict,
        metadata: dict = None,
    ) -> List[dict]:
        """
        Build a full structured audit trail from all pipeline metadata.
        Falls back to translation_stats-only mode if metadata not provided.
        """
        explanations: List[dict] = []

        if metadata is None:
            # Legacy mode: only explain multilingual stats
            explanations += self._explain_multilingual(translation_stats)
            return explanations

        # ── Step 3: Domain Detection ────────────────────────────
        explanations += self._explain_domain(metadata.get("domain_info", {}))

        # ── Step 4: Schema Classification ──────────────────────
        explanations += self._explain_schema(
            metadata.get("schema_mapping", {}),
            metadata.get("strategies", {}),
        )

        # ── Step 5: Multilingual ────────────────────────────────
        explanations += self._explain_multilingual(translation_stats)

        # ── Step 7: String Pre-cleaning ─────────────────────────
        explanations += self._explain_precleaning(metadata)

        # ── Step 8: Entity Resolution ───────────────────────────
        explanations += self._explain_entity_resolution(metadata)

        # ── Step 9: Deduplication ───────────────────────────────
        explanations += self._explain_deduplication(metadata)

        # ── Step 10: Imputation ─────────────────────────────────
        explanations += self._explain_imputation(metadata)

        # ── Step 10b: Outliers ──────────────────────────────────
        explanations += self._explain_outliers(metadata)

        # ── Step 7b: Currency Conversion ────────────────────────
        explanations += self._explain_currency(metadata)

        # ── Step 11: Validation ─────────────────────────────────
        explanations += self._explain_validation(metadata)

        # ── Pipeline Summary ────────────────────────────────────
        explanations += self._explain_summary(metadata)

        return explanations

    # ─────────────────────────────────────────────────────────────
    # Step 3: Domain Detection
    # ─────────────────────────────────────────────────────────────
    def _explain_domain(self, domain_info: dict) -> List[dict]:
        if not domain_info:
            return []
        entries = []

        domain     = domain_info.get("domain", "Generic")
        intent     = domain_info.get("intent", "Non-Predictive Business")
        sub_intent = domain_info.get("sub_intent", "")
        confidence = domain_info.get("confidence", "?")
        method     = domain_info.get("method", "")
        reasoning  = domain_info.get("reasoning", "")
        targets    = domain_info.get("target_variables", [])
        is_ts      = domain_info.get("is_time_series", False)
        has_ml     = domain_info.get("has_multilingual_data", False)
        special    = domain_info.get("special_characteristics", "")

        entries.append({
            "step": "Domain Detection",
            "step_number": 3,
            "column": "DATASET",
            "task": "Domain & Intent Detection",
            "original": "",
            "cleaned": f"{domain} / {intent}",
            "explanation": (
                f"Detected domain: **{domain}** (Intent: {intent}"
                + (f", Sub: {sub_intent}" if sub_intent else "")
                + f"). Confidence: {confidence}. Method: {method}."
                + (f" — {reasoning}" if reasoning else "")
            ),
            "severity": "detect",
            "icon": "🔍",
        })

        if targets:
            entries.append({
                "step": "Domain Detection",
                "step_number": 3,
                "column": "DATASET",
                "task": "Target Variable Detection",
                "original": "",
                "cleaned": str(targets),
                "explanation": (
                    f"Identified {len(targets)} prediction target column(s): {', '.join(targets)}. "
                    "These will use 'leave_empty' imputation — rows with missing targets will be dropped."
                ),
                "severity": "llm",
                "icon": "🎯",
            })

        if is_ts:
            entries.append({
                "step": "Domain Detection",
                "step_number": 3,
                "column": "DATASET",
                "task": "Time-Series Detection",
                "original": "",
                "cleaned": "Time-series ordering detected",
                "explanation": (
                    "Dataset contains date/time columns with temporal ordering. "
                    "Numeric imputation will prefer fill_forward/fill_interpolate over mean/median."
                ),
                "severity": "info",
                "icon": "📅",
            })

        if has_ml:
            entries.append({
                "step": "Domain Detection",
                "step_number": 3,
                "column": "DATASET",
                "task": "Multilingual Data Flag",
                "original": "",
                "cleaned": "Non-ASCII / multilingual content detected",
                "explanation": (
                    "LLM detected non-ASCII (multilingual) values in the dataset. "
                    "Schema classification will flag these columns for translation or transliteration."
                ),
                "severity": "info",
                "icon": "🌐",
            })

        if special:
            entries.append({
                "step": "Domain Detection",
                "step_number": 3,
                "column": "DATASET",
                "task": "Special Characteristics",
                "original": "",
                "cleaned": special[:120],
                "explanation": f"LLM noted special characteristics: {special}",
                "severity": "info",
                "icon": "📌",
            })

        return entries

    # ─────────────────────────────────────────────────────────────
    # Step 4: Schema Classification
    # ─────────────────────────────────────────────────────────────
    def _explain_schema(self, schema_mapping: dict, strategies: dict) -> List[dict]:
        entries = []
        if not schema_mapping:
            return entries

        for col, info in schema_mapping.items():
            sem_type  = info.get("semantic_type", "?")
            impute    = info.get("imputation_strategy", "leave_empty")
            reasoning = info.get("imputation_reasoning", "")
            desc      = info.get("description", "")
            is_crit   = info.get("is_critical_business", False)
            is_target = info.get("is_target", False)
            non_ascii = info.get("non_ascii_ratio", 0)
            needs_ml  = info.get("needs_multilingual", False)

            # Build explanation
            flags = []
            if is_crit:
                flags.append("⚠️ Critical Business Field — no statistical imputation allowed")
            if is_target:
                flags.append("🎯 Target Variable — missing rows will be dropped")
            if needs_ml:
                flags.append(f"🌐 Multilingual ({non_ascii:.1%} non-ASCII)")

            explanation = f"Classified as **{sem_type}** via {desc}. Imputation: `{impute}`."
            if reasoning:
                explanation += f" Reason: {reasoning}"
            if flags:
                explanation += " | " + " | ".join(flags)

            severity = "llm" if "LLM" in desc else "detect"
            icon = _SEVERITY_ICONS.get(severity, "🔍")
            if is_crit:
                icon = "🔒"
            elif is_target:
                icon = "🎯"
            elif needs_ml:
                icon = "🌐"

            entries.append({
                "step": "Schema Classification",
                "step_number": 4,
                "column": col,
                "task": f"Column Type: {sem_type}",
                "original": "",
                "cleaned": f"{sem_type} → {impute}",
                "explanation": explanation,
                "severity": severity,
                "icon": icon,
            })

        return entries

    # ─────────────────────────────────────────────────────────────
    # Step 5: Multilingual Translation & Transliteration
    # ─────────────────────────────────────────────────────────────
    def _explain_multilingual(self, translation_stats: dict) -> List[dict]:
        entries = []
        if not translation_stats:
            return entries

        for col, stats in translation_stats.items():
            mapping  = stats.get("mapping", {})
            task     = stats.get("task", "Unknown")
            ascii_n  = stats.get("ascii_normalized", 0)
            llm_done = stats.get("llm_translated", stats.get("items_processed", 0))

            # Only non-identity mappings (actual changes)
            changes = {k: v for k, v in mapping.items() if str(k).strip() != str(v).strip()}

            if not changes and ascii_n == 0 and llm_done == 0:
                continue

            # Summary entry
            entries.append({
                "step": "Multilingual Processing",
                "step_number": 5,
                "column": col,
                "task": task,
                "original": f"{len(mapping)} unique values",
                "cleaned": f"{len(changes)} values changed",
                "explanation": (
                    f"**{task}** on column `{col}`: "
                    f"{ascii_n} values normalized by ASCII rules, "
                    f"{llm_done} values processed by LLM, "
                    f"{len(changes)} distinct values were changed."
                ),
                "severity": "change" if changes else "info",
                "icon": "🌐" if "Translit" not in task else "🔤",
            })

            # Individual transformation entries (up to 15)
            for original, cleaned in list(changes.items())[:15]:
                entries.append({
                    "step": "Multilingual Processing",
                    "step_number": 5,
                    "column": col,
                    "task": task,
                    "original": str(original),
                    "cleaned": str(cleaned),
                    "explanation": self._generate_explanation(str(original), str(cleaned), task, col),
                    "severity": "change",
                    "icon": "🔄",
                })

        return entries

    # ─────────────────────────────────────────────────────────────
    # Step 7: String Pre-cleaning
    # ─────────────────────────────────────────────────────────────
    def _explain_precleaning(self, metadata: dict) -> List[dict]:
        entries = []
        schema   = metadata.get("schema_mapping", {})
        strats   = metadata.get("strategies", {})

        # Document what normalization was applied per column
        norm_applied: dict[str, list] = {}
        for col, strat in strats.items():
            norm = strat.get("normalization", "none") if isinstance(strat, dict) else strat.normalization
            if norm not in ("none", ""):
                norm_applied.setdefault(norm, []).append(col)

        # Group by normalization type
        norm_labels = {
            "normalize_email":    ("Email Normalization",    "Lowercased, stripped extra characters, extracted valid email address"),
            "normalize_phone":    ("Phone Normalization",    "Removed non-digit characters, stripped country code (91/1), validated length 7–15 digits"),
            "title_case":        ("Title Case",              "Applied title-case formatting to name/location field"),
            "uppercase_strip":   ("Uppercase + Strip",       "Converted to uppercase and stripped leading/trailing whitespace"),
            "standardize_case":  ("Case Standardization",   "Normalized casing and applied fuzzy spelling correction for low-cardinality categories"),
            "coerce_numeric":    ("Numeric Coercion",        "Parsed numeric values from mixed-format strings (e.g. '₹100', '1,234')"),
            "parse_dates":       ("Date Parsing",            "Standardized date formats to ISO 8601 (YYYY-MM-DD)"),
            "transliterate_name": ("Name Transliteration",  "Applied to name column (see Multilingual tab)"),
            "translate_to_english": ("Value Translation",   "Applied to category/location column (see Multilingual tab)"),
        }

        for norm, cols in norm_applied.items():
            label, desc = norm_labels.get(norm, (norm, f"Applied {norm} transformation"))
            entries.append({
                "step": "String Pre-cleaning",
                "step_number": 7,
                "column": ", ".join(cols[:8]) + ("..." if len(cols) > 8 else ""),
                "task": label,
                "original": f"{len(cols)} column(s)",
                "cleaned": norm,
                "explanation": f"**{label}**: {desc}. Applied to: `{', '.join(cols[:5])}{'...' if len(cols)>5 else ''}`.",
                "severity": "fix",
                "icon": "✨",
            })

        # Currency conversion comes in Step 7 too — handled in _explain_currency
        # Quality filter note
        entries.append({
            "step": "String Pre-cleaning",
            "step_number": 7,
            "column": "DATASET",
            "task": "Unicode Normalization",
            "original": "",
            "cleaned": "NFC normalization + sentinel string cleanup",
            "explanation": (
                "All string columns were NFC-normalized (fixes composed vs decomposed unicode). "
                "Sentinel values ('nan', 'none', 'null', 'n/a', 'unknown', '-', '#N/A') were converted to real NaN."
            ),
            "severity": "fix",
            "icon": "🔧",
        })

        return entries

    # ─────────────────────────────────────────────────────────────
    # Step 8: Entity Resolution
    # ─────────────────────────────────────────────────────────────
    def _explain_entity_resolution(self, metadata: dict) -> List[dict]:
        entries = []
        dedup_changes = metadata.get("dedup_changes", [])

        # Entity resolution records are those with "Entity Resolution" reason
        er_records = [
            c for c in dedup_changes
            if any("Entity" in str(r) or "Fuzzy" in str(r)
                   for r in c.get("reasons", {}).keys())
        ]

        if not er_records:
            entries.append({
                "step": "Entity Resolution",
                "step_number": 8,
                "column": "DATASET",
                "task": "Fuzzy Name Clustering",
                "original": "",
                "cleaned": "No entity clusters found",
                "explanation": (
                    "Entity resolution scanned name columns for fuzzy variants "
                    "(phonetic matches, transliteration variants, minor spelling differences). "
                    "No clusters requiring consolidation were found."
                ),
                "severity": "info",
                "icon": "👥",
            })
        else:
            entries.append({
                "step": "Entity Resolution",
                "step_number": 8,
                "column": "DATASET",
                "task": "Fuzzy Name Clustering",
                "original": f"{len(er_records)} variants",
                "cleaned": f"{len(er_records)} clusters resolved",
                "explanation": (
                    f"Entity resolver built fuzzy name clusters and unified {len(er_records)} "
                    "variant name groups into canonical forms."
                ),
                "severity": "change",
                "icon": "👥",
            })
            for record in er_records[:10]:
                entries.append({
                    "step": "Entity Resolution",
                    "step_number": 8,
                    "column": record.get("column", "?"),
                    "task": "Name Cluster Unified",
                    "original": str(record.get("Original", "?")),
                    "cleaned": str(record.get("Corrected", "?")),
                    "explanation": (
                        f"Variant `{record.get('Original')}` → canonical `{record.get('Corrected')}`. "
                        f"Cluster size: {record.get('cluster_size', '?')}. "
                        f"Reasons: {', '.join(record.get('reasons', {}).keys())}"
                    ),
                    "severity": "change",
                    "icon": "🔗",
                })

        return entries

    # ─────────────────────────────────────────────────────────────
    # Step 9: Deduplication
    # ─────────────────────────────────────────────────────────────
    def _explain_deduplication(self, metadata: dict) -> List[dict]:
        entries = []
        initial   = metadata.get("initial_rows", 0)
        final     = metadata.get("final_rows", 0)
        changes   = metadata.get("dedup_changes", [])
        clusters  = metadata.get("dedup_cluster_report", [])

        removed   = initial - final
        n_clusters = len(clusters)
        n_changes  = len(changes)

        entries.append({
            "step": "Deduplication",
            "step_number": 9,
            "column": "DATASET",
            "task": "Exact + Fuzzy Deduplication",
            "original": f"{initial:,} rows",
            "cleaned": f"{final:,} rows",
            "explanation": (
                f"Deduplication removed {removed:,} rows across {n_clusters} clusters, "
                f"consolidating {n_changes} name/entity variants. "
                f"Methods: exact match (hash-based) + fuzzy match (token sort ratio ≥ 85%)."
                if removed > 0 else
                "No duplicate rows found. Dataset is already fully unique."
            ),
            "severity": "change" if removed > 0 else "info",
            "icon": "🗑️" if removed > 0 else "✅",
        })

        # Per-cluster detail (up to 12)
        for cluster in clusters[:12]:
            orig   = cluster.get("Original", "?")
            corr   = cluster.get("Corrected", "?")
            size   = cluster.get("cluster_size", 1)
            reasons = cluster.get("reasons", {})
            reason_str = " + ".join(f"{v}× {k}" for k, v in reasons.items()) if reasons else "Exact duplicate"

            entries.append({
                "step": "Deduplication",
                "step_number": 9,
                "column": cluster.get("column", "DATASET"),
                "task": "Duplicate Cluster Merged",
                "original": str(orig),
                "cleaned": str(corr),
                "explanation": (
                    f"Merged {size - 1} duplicate(s) of `{orig}` into canonical form `{corr}`. "
                    f"Signal: {reason_str}."
                ),
                "severity": "remove",
                "icon": "🔗",
            })

        return entries

    # ─────────────────────────────────────────────────────────────
    # Step 10: Imputation
    # ─────────────────────────────────────────────────────────────
    def _explain_imputation(self, metadata: dict) -> List[dict]:
        entries = []

        # LLM Contextual Rules
        smart_rules = metadata.get("smart_imputation_rules", [])
        for rule in smart_rules:
            col         = rule.get("target_column", rule.get("column", "?"))
            condition   = rule.get("condition", "always")
            fill_value  = rule.get("fill_value", "?")
            confidence  = rule.get("confidence", 0)
            rows_filled = rule.get("rows_filled", 0)
            severity    = "fix" if rows_filled > 0 else "info"

            entries.append({
                "step": "Smart Imputation",
                "step_number": 10,
                "column": col,
                "task": "LLM Contextual Rule",
                "original": f"Missing when: {condition}",
                "cleaned": f"→ '{fill_value}' ({rows_filled} rows, {confidence}% confidence)",
                "explanation": (
                    f"LLM rule: IF `{condition}` THEN fill `{col}` with '{fill_value}'. "
                    f"Applied to {rows_filled} row(s) with {confidence}% confidence."
                ),
                "severity": severity,
                "icon": "🤖",
            })

        # Statistical Fallback
        stat_log = metadata.get("statistical_imputation_log", [])
        for s in stat_log:
            col        = s.get("column", "?")
            strategy   = s.get("strategy", "?")
            fill_val   = s.get("fill_value", "?")
            rows_filled = s.get("rows_filled", 0)
            pct        = s.get("missing_pct", 0)
            skew       = s.get("skewness", None)

            # Build context note
            context = ""
            if strategy == "fill_median" and skew is not None:
                context = f" (skewness={skew:.2f} — median preferred over mean)"
            elif strategy == "fill_mode":
                top = s.get("top_distribution", {})
                top_val = list(top.keys())[0] if top else "?"
                context = f" (most common value: '{top_val}')"
            elif strategy in ("fill_forward", "fill_backward"):
                context = " (time-series ordered propagation)"
            elif strategy == "fill_interpolate":
                context = " (linear interpolation between known values)"

            # Get AI reasoning for this col from schema
            schema_mapping = metadata.get("schema_mapping", {})
            ai_reason = schema_mapping.get(col, {}).get("imputation_reasoning", "")

            explanation = (
                f"Statistical imputation on `{col}` using **{strategy}**{context}. "
                f"Filled {rows_filled} missing rows ({pct}% of column) with `{fill_val}`."
            )
            if ai_reason:
                explanation += f" AI reasoning: {ai_reason}"

            entries.append({
                "step": "Smart Imputation",
                "step_number": 10,
                "column": col,
                "task": f"Statistical: {strategy}",
                "original": f"{pct}% missing ({rows_filled} rows)",
                "cleaned": f"Filled with '{fill_val}'",
                "explanation": explanation,
                "severity": "fix",
                "icon": "🧩",
            })

        if not smart_rules and not stat_log:
            entries.append({
                "step": "Smart Imputation",
                "step_number": 10,
                "column": "DATASET",
                "task": "No Imputation Needed",
                "original": "",
                "cleaned": "All values present or intentionally left empty",
                "explanation": (
                    "No missing values required imputation. "
                    "Critical business fields (IDs, names, emails) were correctly left as NaN rather than fabricated."
                ),
                "severity": "info",
                "icon": "✅",
            })

        return entries

    # ─────────────────────────────────────────────────────────────
    # Step 10b: Outlier Handling
    # ─────────────────────────────────────────────────────────────
    def _explain_outliers(self, metadata: dict) -> List[dict]:
        entries = []
        outlier_stats = metadata.get("outlier_stats", {})
        if not outlier_stats:
            return entries

        for col, stats in outlier_stats.items():
            outliers_found = stats.get("outliers_found", 0)
            method         = stats.get("method", "IQR")
            lower          = stats.get("lower_bound")
            upper          = stats.get("upper_bound")
            domain_fixed   = stats.get("domain_outliers_fixed", 0)

            if outliers_found == 0 and domain_fixed == 0:
                continue

            bounds_str = ""
            if lower is not None and upper is not None:
                bounds_str = f" (bounds: {lower:.2f}–{upper:.2f})"

            explanation = f"Outlier detection on `{col}` via {method}{bounds_str}."
            if outliers_found > 0:
                explanation += f" Clipped {outliers_found} statistical outlier(s) to IQR boundary."
            if domain_fixed > 0:
                explanation += f" Fixed {domain_fixed} domain-boundary violation(s) (e.g. negative age, out-of-range BMI)."

            entries.append({
                "step": "Outlier Handling",
                "step_number": 10,
                "column": col,
                "task": f"Outlier Detection: {method}",
                "original": f"{outliers_found + domain_fixed} outlier(s)",
                "cleaned": f"Clipped/nullified{bounds_str}",
                "explanation": explanation,
                "severity": "fix" if (outliers_found + domain_fixed) > 0 else "info",
                "icon": "📊",
            })

        return entries

    # ─────────────────────────────────────────────────────────────
    # Step 7b: Currency Conversion
    # ─────────────────────────────────────────────────────────────
    def _explain_currency(self, metadata: dict) -> List[dict]:
        entries = []
        currency_report = metadata.get("currency_report", [])
        if not currency_report:
            entries.append({
                "step": "Currency Conversion",
                "step_number": 7,
                "column": "DATASET",
                "task": "Currency Detection",
                "original": "",
                "cleaned": "No foreign currencies detected",
                "explanation": "No columns with mixed currency symbols (₹, $, €, £, ¥) were found. All monetary values are assumed to be in the same currency.",
                "severity": "info",
                "icon": "💱",
            })
            return entries

        for cr in currency_report:
            col_name   = cr.get("column", "?")
            converted  = cr.get("rows_converted", 0)
            assumed    = cr.get("rows_assumed_inr", 0)
            failed     = cr.get("rows_failed", 0)
            rates      = cr.get("rates_used", {})
            detected   = cr.get("currencies_found", {})

            rate_str = ", ".join(f"1 {c}=₹{r:,.2f}" for c, r in rates.items())
            detected_str = ", ".join(f"{c}: {cnt}" for c, cnt in detected.items())

            entries.append({
                "step": "Currency Conversion",
                "step_number": 7,
                "column": col_name,
                "task": "Mixed Currency → INR",
                "original": detected_str or "Mixed currencies",
                "cleaned": f"{converted} rows converted to INR",
                "explanation": (
                    f"Column `{col_name}` had mixed currency values: {detected_str}. "
                    f"Exchange rates applied: {rate_str}. "
                    f"Converted: {converted}, assumed INR (no symbol): {assumed}"
                    + (f", failed to parse: {failed}" if failed else "") + "."
                ),
                "severity": "change",
                "icon": "💱",
            })

        return entries

    # ─────────────────────────────────────────────────────────────
    # Step 11: Validation
    # ─────────────────────────────────────────────────────────────
    def _explain_validation(self, metadata: dict) -> List[dict]:
        entries = []
        validation = metadata.get("validation", {})
        if not validation:
            return entries

        confidence = validation.get("overall_confidence", 0)
        issues     = validation.get("issues", [])

        entries.append({
            "step": "Validation",
            "step_number": 11,
            "column": "DATASET",
            "task": "Post-Cleaning Quality Check",
            "original": "",
            "cleaned": f"{confidence}% confidence score",
            "explanation": (
                f"Post-cleaning validation score: **{confidence}%**. "
                + (f"{len(issues)} issue(s) detected." if issues else "All quality checks passed.")
            ),
            "severity": "fix" if confidence >= 80 else "warning",
            "icon": "✅" if confidence >= 80 else "⚠️",
        })

        for issue in issues:
            entries.append({
                "step": "Validation",
                "step_number": 11,
                "column": "DATASET",
                "task": "Validation Issue",
                "original": "",
                "cleaned": str(issue),
                "explanation": f"Validation flagged: {issue}",
                "severity": "warning",
                "icon": "⚠️",
            })

        return entries

    # ─────────────────────────────────────────────────────────────
    # Pipeline Summary
    # ─────────────────────────────────────────────────────────────
    def _explain_summary(self, metadata: dict) -> List[dict]:
        entries = []
        initial       = metadata.get("initial_rows", 0)
        final         = metadata.get("final_rows", 0)
        exec_time     = metadata.get("execution_time_sec", 0)
        domain        = metadata.get("domain", "Generic")
        intent        = metadata.get("dataset_intent", "")
        sub_intent    = metadata.get("sub_intent", "")
        validation    = metadata.get("validation", {})
        confidence    = validation.get("overall_confidence", 0)

        smart_rules  = metadata.get("smart_imputation_rules", [])
        stat_rules   = metadata.get("statistical_imputation_log", [])
        ml_stats     = metadata.get("translation_stats", {})
        clusters     = metadata.get("dedup_cluster_report", [])
        outlier_stats = metadata.get("outlier_stats", {})
        currency_rpt = metadata.get("currency_report", [])

        # Count meaningful changes
        ml_changes  = sum(len({k: v for k, v in s.get("mapping", {}).items() if k != v}) for s in ml_stats.values())
        dedup_removed = initial - final
        impute_filled = sum(r.get("rows_filled", 0) for r in stat_rules) + sum(r.get("rows_filled", 0) for r in smart_rules)
        outlier_count = sum(s.get("outliers_found", 0) + s.get("domain_outliers_fixed", 0) for s in outlier_stats.values())
        currency_converted = sum(cr.get("rows_converted", 0) for cr in currency_rpt)

        entries.append({
            "step": "Pipeline Complete",
            "step_number": 12,
            "column": "DATASET",
            "task": "Summary",
            "original": f"{initial:,} rows",
            "cleaned": f"{final:,} rows, {confidence}% quality score",
            "explanation": (
                f"✅ **IntelliClean pipeline completed in {exec_time:.1f}s**. "
                f"Domain: {domain} ({intent}" + (f"/{sub_intent}" if sub_intent else "") + f"). "
                f"Rows: {initial:,} → {final:,} ({dedup_removed:,} duplicates removed). "
                f"Missing values filled: {impute_filled:,}. "
                f"Multilingual values translated/transliterated: {ml_changes:,}. "
                f"Outliers handled: {outlier_count:,}. "
                + (f"Currency rows converted: {currency_converted:,}. " if currency_converted else "")
                + f"Final quality score: {confidence}%."
            ),
            "severity": "fix",
            "icon": "🏁",
        })

        return entries

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────
    def _generate_explanation(
        self, original: str, cleaned: str, task: str, column: str
    ) -> str:
        """Generate a concise human-readable explanation for a single value transformation."""
        if not original or not cleaned:
            return f"Processed value in '{column}' during {task}."

        if original.lower().strip() == cleaned.lower().strip():
            return f"Normalized casing of '{original}' → '{cleaned}' in `{column}`."

        if "transliterat" in task.lower():
            return f"Phonetically transliterated non-Latin script '{original}' → Latin script '{cleaned}' in `{column}`."

        if "translat" in task.lower():
            return f"Translated non-English value '{original}' → English equivalent '{cleaned}' in `{column}`."

        if original.isascii() and cleaned.isascii():
            return f"Standardized '{original}' → canonical form '{cleaned}' in `{column}`."

        return f"Transformed '{original}' → '{cleaned}' during {task} on `{column}`."
