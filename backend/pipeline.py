"""
Pipeline orchestrator: ties all components together into a
sequential cleaning workflow.

Pipeline order:
  1.  Load dataset
  2.  Profile (detect scripts, quality score)
  3.  Domain detection (LLM-primary, keywords as hint)
  4.  Schema classification (heuristic + LLM, domain-aware)
  5.  Multilingual translation (categories) and transliteration (names)
       — runs AFTER schema so only correctly-typed columns are processed
  6.  Plan cleaning strategies + smart imputation rules
  7.  String pre-cleaning (whitespace, unicode normalization)
  8.  Entity resolution (fuzzy name clustering)
  9.  Deduplication (exact + fuzzy matching)
  10. Smart imputation (LLM rules + statistical fallback)
  11. Validation (confidence scoring)
  12. Export + audit trail
"""
import time
import numpy as np
import pandas as pd
from typing import Callable

from backend.loader import UniversalLoader
from backend.profiler import DatasetProfiler
from backend.domain_profiler import DomainProfiler
from backend.validator import Validator

from agents.llm_client import LMStudioClient
from agents.schema_agent import SchemaAgent
from agents.planner_agent import PlannerAgent
from agents.validation_agent import ValidationAgent
from agents.explanation_agent import ExplanationAgent

from cleaning.string_cleaner import StringCleaner
from cleaning.multilingual import MultilingualEngine
from cleaning.standardizer import Standardizer
from cleaning.entity_resolution import EntityResolver
from cleaning.deduplication import DeduplicationEngine
from cleaning.missing_values import SmartImputer
from cleaning.outliers import OutlierHandler
from cleaning.currency_converter import CurrencyConverter


class PipelineOrchestrator:
    """
    Master controller that executes the full 12-step cleaning pipeline.
    """

    def __init__(self, df: pd.DataFrame, log_callback: Callable[[str], None] = print):
        self.df = df
        self.log = log_callback

    def execute(self) -> tuple:
        """Run the entire pipeline. Returns (cleaned_df, metadata_dict)."""
        self.log("=" * 60)
        self.log("  IntelliClean AI — Starting Data Cleaning Pipeline")
        self.log("=" * 60)
        start_time = time.time()

        # Shared LLM client (single instance, reused across all agents)
        llm = LMStudioClient()

        # ── Step 1: Load & initial metrics ────────────────────────
        self.log("\n[Step 1] Dataset Loaded")
        df = self.df.copy()
        initial_rows = len(df)
        self.log(f"  Rows: {initial_rows} | Columns: {len(df.columns)}")
        self.log(f"  Columns: {list(df.columns)}")

        # ── Step 2: Profile (detect scripts, quality score) ────────
        self.log("\n[Step 2] Dataset Profiling")
        profiler = DatasetProfiler(df)
        profile_data = profiler.profile()
        self.log(f"  Quality Score: {profile_data['quality_score']}/100")
        self.log(f"  Missing Cells: {profile_data['total_missing_cells']}")
        self.log(f"  Exact Duplicates: {profile_data['exact_duplicate_rows']}")

        # Report multilingual columns found during profiling
        ml_cols_detected = []
        for col, stats in profile_data.get("column_statistics", {}).items():
            if stats.get("non_ascii_ratio", 0) > 0.01:
                scripts = stats.get("scripts", {})
                self.log(f"  [Profiler] '{col}' has non-ASCII content: {scripts}")
                ml_cols_detected.append(col)

        # ── Step 3: Domain Detection (LLM-primary) ────────────────
        self.log("\n[Step 3] Domain & Intent Detection")
        domain_info = DomainProfiler(llm_client=llm).detect_domain(df, log_callback=self.log)
        domain                = domain_info["domain"]
        dataset_intent        = domain_info.get("intent", "Non-Predictive Business")
        sub_intent            = domain_info.get("sub_intent", "Master Data")
        target_variables      = domain_info.get("target_variables", [])
        is_time_series        = domain_info.get("is_time_series", False)
        has_multilingual_data = domain_info.get("has_multilingual_data", False)
        special_characteristics = domain_info.get("special_characteristics", "")

        self.log(
            f"  Domain: {domain} | Intent: {dataset_intent} | Sub: {sub_intent} "
            f"| Confidence: {domain_info['confidence']} | Method: {domain_info['method']}"
        )
        self.log(f"  Reasoning: {domain_info['reasoning']}")
        if target_variables:
            self.log(f"  Target Variables: {target_variables}")
        if is_time_series:
            self.log(f"  Time-Series Dataset Detected")
        if has_multilingual_data:
            self.log(f"  Multilingual Data Detected by Domain Agent")
        if special_characteristics:
            self.log(f"  Special Characteristics: {special_characteristics}")

        # ── Step 4: Schema Classification (heuristic + LLM, domain-aware) ──
        self.log("\n[Step 4] AI Schema Classification")
        schema_agent   = SchemaAgent(llm)
        schema_mapping = schema_agent.classify_columns(
            df,
            log_callback=self.log,
            dataset_intent=dataset_intent,
            target_variables=target_variables,
            is_time_series=is_time_series,
            domain=domain,
            domain_reasoning=domain_info.get("reasoning", ""),
            has_multilingual_data=has_multilingual_data,
        )

        # ── Step 5: Multilingual Translation & Transliteration ────
        # Runs HERE (after schema) so only correctly-typed columns are processed.
        # Schema tells us WHICH columns need multilingual processing and HOW
        # (translate_to_english for Categorical/Location, transliterate for Name).
        self.log("\n[Step 5] Multilingual Translation & Transliteration")
        ml_engine   = MultilingualEngine(llm)
        standardizer = Standardizer(ml_engine)

        multilingual_cols_processed = []
        for col, col_schema in schema_mapping.items():
            if col not in df.columns:
                continue
            if not col_schema.needs_multilingual:
                continue

            sem_type = col_schema.semantic_type

            if sem_type in ("Categorical", "Location"):
                self.log(
                    f"  [Translate] '{col}' ({sem_type}) — "
                    f"{df[col].nunique()} unique values"
                )
                df = standardizer.apply(df, col, "translate_to_english")
                multilingual_cols_processed.append((col, "translated"))

            elif sem_type == "Name":
                self.log(
                    f"  [Transliterate] '{col}' ({sem_type}) — "
                    f"{df[col].nunique()} unique names"
                )
                df = standardizer.apply(df, col, "transliterate_name")
                multilingual_cols_processed.append((col, "transliterated"))

        if not multilingual_cols_processed:
            self.log("  No multilingual columns detected — skipping.")

        # ── Step 6: Plan Cleaning Strategies + Smart Imputation Rules ──
        self.log("\n[Step 6] Planning Cleaning Strategies")
        planner   = PlannerAgent(llm)
        strategies = planner.plan(
            schema_mapping, log_callback=self.log,
            domain=domain, dataset_intent=dataset_intent,
        )

        # Generate smart imputation rules (domain + intent aware)
        smart_rules = planner.generate_smart_imputation_rules(
            df, schema_mapping, log_callback=self.log,
            domain=domain, dataset_intent=dataset_intent,
        )

        # Capture pre-cleaning missing value metrics
        missing_before = df.isna().sum().to_dict()

        # Drop rows with missing target variables (Predictive only)
        if dataset_intent == "Predictive" and target_variables:
            valid_targets = [t for t in target_variables if t in df.columns]
            if valid_targets:
                rows_before = len(df)
                df = df.dropna(subset=valid_targets).reset_index(drop=True)
                dropped = rows_before - len(df)
                if dropped > 0:
                    self.log(
                        f"  [Predictive] Dropped {dropped} rows with missing "
                        f"target variable(s): {valid_targets}"
                    )

        # ── Step 7: String Pre-cleaning (whitespace, unicode) ──────
        self.log("\n[Step 7] String Pre-cleaning")
        df = StringCleaner.clean_all_string_columns(df)

        # Row-Level Quality Filtering (after string cleaning for accuracy)
        from cleaning.quality_filter import QualityFilter
        q_filter = QualityFilter(df, schema_mapping)
        df = q_filter.filter_useless_rows()
        self.log(f"  [Quality Filter] {q_filter.get_report()}")

        # Currency Detection & Conversion
        self.log("  [Currency] Detecting and converting mixed currencies to INR...")
        currency_converter = CurrencyConverter()
        df, currency_report = currency_converter.convert_all(df)
        if currency_report:
            self.log(f"  [Currency] Converted {len(currency_report)} column(s) to INR (₹)")
        else:
            self.log("  [Currency] No mixed-currency columns detected.")

        # Single-Column Standardization (non-multilingual strategies)
        self.log("  [Standardization] Applying column-level normalization...")
        _ML_NORMS = {"transliterate_name", "translate_to_english"}
        for col, strat in strategies.items():
            if strat.normalization == "none" or col not in df.columns:
                continue
            # Multilingual already handled in Step 5 — skip re-applying
            if strat.normalization in _ML_NORMS:
                continue
            if strat.normalization in [
                "normalize_email", "normalize_phone", "title_case",
                "uppercase_strip", "standardize_case", "coerce_numeric", "parse_dates",
            ]:
                self.log(f"    -> '{col}': {strat.normalization}")
                df = standardizer.apply(df, col, strat.normalization)

        # Domain-Specific Rules
        self.log("  [Domain Rules] Applying domain-specific cleaning rules...")
        df = self._apply_domain_rules(df, domain, dataset_intent)

        # ── Step 8: Entity Resolution (fuzzy name clustering) ──────
        self.log("\n[Step 8] Entity Resolution")
        name_cols = [
            col for col, strat in strategies.items()
            if strat.normalization == "transliterate_name" and col in df.columns
        ]

        entity_clusters_found = 0
        for name_col in name_cols:
            if name_col in standardizer.stats:
                raw_mapping = standardizer.stats[name_col].get("mapping", {})
                if raw_mapping:
                    resolver = EntityResolver()
                    unified_mapping = resolver.build_name_clusters(raw_mapping)
                    entity_clusters_found += 1

                    original_values = df[name_col].dropna().unique()
                    full_map = {}
                    for v in original_values:
                        v_str = str(v).strip()
                        full_map[v_str] = unified_mapping.get(v_str, v_str)

                    df[name_col] = df[name_col].apply(
                        lambda x: full_map.get(str(x).strip(), x) if pd.notna(x) else pd.NA
                    )
                    self.log(f"  [EntityResolver] '{name_col}': {len(unified_mapping)} name clusters resolved")

        if not name_cols:
            self.log("  No name columns for entity resolution — skipping.")

        # ── Step 9: Deduplication (exact + fuzzy matching) ─────────
        self.log("\n[Step 9] Deduplication")
        dedup_strategies = {col: strat.deduplication for col, strat in strategies.items()}

        _MASTER_DATA_DOMAINS = {
            "CRM", "HR", "Healthcare", "Real Estate", "Insurance",
            "Pharma", "Legal", "Education", "Government",
        }
        is_master_data = (
            dataset_intent == "Non-Predictive Business" or
            domain in _MASTER_DATA_DOMAINS
        )
        dedup = DeduplicationEngine(
            df, dedup_strategies,
            dataset_intent=dataset_intent,
            keep_all_rows=not is_master_data,
            log_callback=self.log,
        )
        df = dedup.execute()
        removed_by_dedup = initial_rows - len(df)
        if removed_by_dedup > 0:
            self.log(f"  Removed {removed_by_dedup} duplicate rows, kept {len(df)} unique records.")
        if dedup.cluster_report:
            self.log(f"  Found {len(dedup.cluster_report)} duplicate clusters.")

        # ── Step 10: Smart Imputation (LLM rules + statistical) ────
        self.log("\n[Step 10] Smart Imputation")
        imputer = SmartImputer()

        # Apply LLM-generated rules first
        self.log("  -> Applying LLM smart imputation rules...")
        df = imputer.apply_smart_rules(df, smart_rules)

        # Statistical fallback for remaining missing values
        self.log("  -> Statistical fallback imputation...")
        for col, strat in strategies.items():
            if col in df.columns and strat.imputation != "leave_empty":
                df = imputer.apply_statistical(df, col, strat.imputation)

        # Outlier Detection & Treatment
        all_numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        outlier_handler  = OutlierHandler(dataset_intent=dataset_intent)
        if all_numeric_cols:
            self.log("\n  [Outliers] Detecting and handling outliers...")
            df = outlier_handler.handle_all_numeric(df, all_numeric_cols)
            total_outliers  = sum(v.get('outliers_found', 0) for v in outlier_handler.stats.values())
            domain_outliers = sum(v.get('domain_outliers_fixed', 0) for v in outlier_handler.stats.values())
            self.log(f"  Statistical outliers clipped: {total_outliers}")
            if domain_outliers > 0:
                self.log(f"  Domain-boundary violations fixed: {domain_outliers}")

        # ── Step 11: Validation (confidence scoring) ───────────────
        self.log("\n[Step 11] Validation & Confidence Scoring")
        validator         = Validator()
        validation_result = validator.validate(df, schema_mapping)
        self.log(f"  Validation Score: {validation_result['overall_confidence']}%")
        if validation_result["issues"]:
            for issue in validation_result["issues"]:
                self.log(f"  [Issue] {issue}")

        # Optional: LLM spot-check
        try:
            val_agent      = ValidationAgent(llm)
            llm_validation = val_agent.spot_check(df, log_callback=self.log)
            validation_result.update(llm_validation)
        except Exception as e:
            self.log(f"  [Warning] LLM validation skipped: {e}")

        # ── Step 12: Export + Audit Trail ─────────────────────────
        self.log("\n[Step 12] Generating Audit Trail")
        explainer = ExplanationAgent(llm)
        all_stats = {**standardizer.stats, **ml_engine.stats}

        # Build a partial metadata dict for the explainer (final metadata not yet assembled)
        partial_meta = {
            "domain_info":              domain_info,
            "domain":                   domain,
            "dataset_intent":           dataset_intent,
            "sub_intent":               sub_intent,
            "target_variables":         target_variables,
            "is_time_series":           is_time_series,
            "has_multilingual_data":    has_multilingual_data,
            "schema_mapping":           {col: s.dict() for col, s in schema_mapping.items()},
            "strategies":               {col: s.dict() for col, s in strategies.items()},
            "smart_imputation_rules":   [
                r.__dict__ if hasattr(r, "__dict__") else r
                for r in imputer.applied_rules
            ],
            "statistical_imputation_log": imputer.statistical_log,
            "dedup_changes":            dedup.dedup_changes,
            "dedup_cluster_report":     dedup.cluster_report,
            "initial_rows":             initial_rows,
            "final_rows":               len(df),
            "validation":               validation_result,
            "outlier_stats":            outlier_handler.stats if all_numeric_cols else {},
            "currency_report":          currency_report,
        }
        explanations = explainer.explain_transformations(all_stats, metadata=partial_meta)

        # Final exact duplicate sweep
        df = df.drop_duplicates().reset_index(drop=True)

        # ── Summary ───────────────────────────────────────────────
        final_rows = len(df)
        exec_time  = time.time() - start_time
        self.log("\n" + "=" * 60)
        self.log(f"  Pipeline Completed in {exec_time:.2f} seconds")
        self.log(f"  Rows: {initial_rows} → {final_rows} "
                 f"({'−' + str(initial_rows - final_rows) if initial_rows > final_rows else '+' + str(final_rows - initial_rows)} rows)")
        self.log(f"  Domain: {domain} ({dataset_intent})")
        self.log(f"  Validation: {validation_result['overall_confidence']}%")
        self.log("=" * 60)

        metadata = {
            "initial_rows":             initial_rows,
            "final_rows":               final_rows,
            "domain":                   domain,
            "dataset_intent":           dataset_intent,
            "sub_intent":               sub_intent,
            "target_variables":         target_variables,
            "is_time_series":           is_time_series,
            "has_multilingual_data":    has_multilingual_data,
            "special_characteristics":  special_characteristics,
            "domain_info":              domain_info,
            "execution_time_sec":       round(exec_time, 2),
            "profile":                  profile_data,
            "schema_mapping":           {col: s.dict() for col, s in schema_mapping.items()},
            "strategies":               {col: s.dict() for col, s in strategies.items()},
            "missing_values_before":    missing_before,
            "translation_stats":        all_stats,
            "multilingual_processed":   multilingual_cols_processed,
            "smart_imputation_rules":   [
                r.__dict__ if hasattr(r, "__dict__") else r
                for r in imputer.applied_rules
            ],
            "statistical_imputation_log": imputer.statistical_log,
            "dedup_changes":            dedup.dedup_changes,
            "dedup_cluster_report":     dedup.cluster_report,
            "validation":               validation_result,
            "explanations":             explanations,
            "outlier_stats":            outlier_handler.stats if all_numeric_cols else {},
            "currency_report":          currency_report,
        }

        return df, metadata

    # ─────────────────────────────────────────────────────────────
    # Domain-specific cleaning rules (Step 7, post-standardization)
    # ─────────────────────────────────────────────────────────────
    def _apply_domain_rules(
        self, df: pd.DataFrame, domain: str, dataset_intent: str
    ) -> pd.DataFrame:
        """Apply domain-specific data cleaning rules after schema standardization."""

        def _col(name):
            """Case-insensitive column lookup."""
            for c in df.columns:
                if c.lower().replace(" ", "_") == name.lower():
                    return c
            return None

        # ── Global Rule: Temporal Paradox (Time Travel) ───────────
        ORDER_HINTS    = ["order", "purchase", "start", "created", "placed", "open"]
        DELIVERY_HINTS = ["delivery", "delivered", "end", "close", "completed", "shipped", "resolved"]

        order_col    = None
        delivery_col = None
        for col in df.columns:
            cl = col.lower()
            if any(h in cl for h in ORDER_HINTS) and "date" in cl and order_col is None:
                order_col = col
            if any(h in cl for h in DELIVERY_HINTS) and "date" in cl and delivery_col is None:
                delivery_col = col

        if order_col and delivery_col:
            order_dt    = pd.to_datetime(df[order_col], errors='coerce')
            delivery_dt = pd.to_datetime(df[delivery_col], errors='coerce')
            paradox_mask  = delivery_dt < order_dt
            paradox_count = int(paradox_mask.sum())
            if paradox_count > 0:
                temp = df.loc[paradox_mask, order_col].copy()
                df.loc[paradox_mask, order_col]    = df.loc[paradox_mask, delivery_col]
                df.loc[paradox_mask, delivery_col] = temp
                self.log(
                    f"  [Global Rule] Fixed {paradox_count} temporal paradoxes "
                    f"(swapped '{delivery_col}' ↔ '{order_col}')"
                )

        # ── Retail ────────────────────────────────────────────────
        if domain == "Retail":
            pri   = _col("priority")
            ctype = _col("customer_type")
            if pri and ctype:
                b2x  = df[ctype].astype(str).str.upper().str.strip().isin(["B2B", "B2C"])
                miss = df[pri].isna() | df[pri].astype(str).str.strip().isin(["", "nan", "None"])
                df.loc[b2x & miss, pri] = "Medium"
                filled = int((b2x & miss).sum())
                if filled > 0:
                    self.log(f"  [Retail] Filled {filled} missing priorities for B2B/B2C customers")

        # ── Finance ───────────────────────────────────────────────
        elif domain == "Finance":
            for col in df.columns:
                col_l = col.lower()
                if any(k in col_l for k in ["amount", "balance", "revenue", "profit"]):
                    if "debit" not in col_l and "loss" not in col_l:
                        if df[col].dtype in [np.float64, np.int64]:
                            neg_count = int((df[col] < 0).sum())
                            if neg_count > 0:
                                df[col] = df[col].clip(lower=0)
                                self.log(f"  [Finance] Clipped {neg_count} negative values in '{col}' to 0")
            pay      = _col("payment_status")
            ord_stat = _col("order_status") or _col("transaction_status")
            if pay and ord_stat:
                mask = (df[ord_stat].astype(str).str.lower() == "delivered") & df[pay].isna()
                if mask.sum() > 0:
                    df.loc[mask, pay] = "Paid"
                    self.log(f"  [Finance] Filled {int(mask.sum())} payment_status = 'Paid' where order delivered")

        # ── Healthcare ────────────────────────────────────────────
        elif domain == "Healthcare":
            age = _col("age")
            if age and df[age].dtype in [np.float64, np.int64]:
                invalid = (df[age] < 0) | (df[age] > 150)
                if int(invalid.sum()) > 0:
                    df.loc[invalid, age] = np.nan
                    self.log(f"  [Healthcare] Nullified {int(invalid.sum())} out-of-range age values")
            bmi = _col("bmi")
            if bmi and df[bmi].dtype in [np.float64, np.int64]:
                invalid = (df[bmi] < 10) | (df[bmi] > 70)
                if int(invalid.sum()) > 0:
                    df.loc[invalid, bmi] = np.nan
                    self.log(f"  [Healthcare] Nullified {int(invalid.sum())} out-of-range BMI values")
            bp = _col("blood_pressure") or _col("systolic")
            if bp and df[bp].dtype in [np.float64, np.int64]:
                invalid = (df[bp] < 60) | (df[bp] > 250)
                if int(invalid.sum()) > 0:
                    df.loc[invalid, bp] = np.nan
                    self.log(f"  [Healthcare] Nullified {int(invalid.sum())} out-of-range blood pressure values")
            self.log("  [Healthcare] Privacy: ID/Name/MRN fields will not be statistically imputed")

        # ── HR ────────────────────────────────────────────────────
        elif domain == "HR":
            sal = _col("salary")
            if sal and df[sal].dtype in [np.float64, np.int64]:
                neg = df[sal] < 0
                if int(neg.sum()) > 0:
                    df.loc[neg, sal] = np.nan
                    self.log(f"  [HR] Nullified {int(neg.sum())} negative salary values")
            self.log("  [HR] Salary and compensation fields will not be statistically imputed")

        # ── E-Commerce ────────────────────────────────────────────
        elif domain == "E-Commerce":
            price = _col("price") or _col("selling_price") or _col("mrp")
            if price and df[price].dtype in [np.float64, np.int64]:
                neg = df[price] < 0
                if int(neg.sum()) > 0:
                    df.loc[neg, price] = np.nan
                    self.log(f"  [E-Commerce] Nullified {int(neg.sum())} negative price values")
            rating = _col("rating") or _col("review_rating")
            if rating and df[rating].dtype in [np.float64, np.int64]:
                max_rating = df[rating].dropna().max()
                upper      = 10 if max_rating > 5 else 5
                invalid    = (df[rating] < 0) | (df[rating] > upper)
                if int(invalid.sum()) > 0:
                    df.loc[invalid, rating] = np.nan
                    self.log(f"  [E-Commerce] Nullified {int(invalid.sum())} out-of-range ratings")

        # ── Logistics ─────────────────────────────────────────────
        elif domain == "Logistics":
            stat  = _col("delivery_status") or _col("status")
            track = _col("tracking_id") or _col("tracking_number")
            if stat and track:
                has_track = df[track].notna() & (df[track].astype(str).str.strip() != "")
                miss_stat = df[stat].isna() | (df[stat].astype(str).str.strip() == "")
                mask = has_track & miss_stat
                if int(mask.sum()) > 0:
                    df.loc[mask, stat] = "In Transit"
                    self.log(f"  [Logistics] Filled {int(mask.sum())} delivery_status = 'In Transit'")

        # ── Manufacturing ─────────────────────────────────────────
        elif domain == "Manufacturing":
            for col in df.columns:
                if any(k in col.lower() for k in ["yield", "quantity", "production", "output"]):
                    if df[col].dtype in [np.float64, np.int64]:
                        neg = df[col] < 0
                        if int(neg.sum()) > 0:
                            df.loc[neg, col] = np.nan
                            self.log(f"  [Manufacturing] Nullified {int(neg.sum())} negative values in '{col}'")

        # ── Agriculture ───────────────────────────────────────────
        elif domain == "Agriculture":
            for col in df.columns:
                if any(k in col.lower() for k in ["yield", "production", "area", "acreage"]):
                    if df[col].dtype in [np.float64, np.int64]:
                        neg = df[col] < 0
                        if int(neg.sum()) > 0:
                            df.loc[neg, col] = np.nan
                            self.log(f"  [Agriculture] Nullified {int(neg.sum())} negative values in '{col}'")

        # ── Education ─────────────────────────────────────────────
        elif domain == "Education":
            gpa = _col("gpa")
            if gpa and df[gpa].dtype in [np.float64, np.int64]:
                invalid = (df[gpa] < 0) | (df[gpa] > 10)
                if int(invalid.sum()) > 0:
                    df.loc[invalid, gpa] = np.nan
                    self.log(f"  [Education] Nullified {int(invalid.sum())} out-of-range GPA values (0-10)")
            for col in df.columns:
                col_l = col.lower()
                if any(k in col_l for k in ["marks", "score", "grade_points"]):
                    if df[col].dtype in [np.float64, np.int64]:
                        invalid = (df[col] < 0) | (df[col] > 100)
                        if int(invalid.sum()) > 0:
                            df.loc[invalid, col] = np.nan
                            self.log(f"  [Education] Nullified {int(invalid.sum())} out-of-range marks in '{col}'")

        # ── IoT ───────────────────────────────────────────────────
        elif domain == "IoT":
            self.log("  [IoT] Sensor data: time-ordered interpolation preferred for numeric columns")

        # ── CRM ───────────────────────────────────────────────────
        elif domain == "CRM":
            self.log("  [CRM] Lead/contact data: identity fields will not be statistically imputed")

        # ── Telecommunications ────────────────────────────────────
        elif domain == "Telecommunications":
            for col in df.columns:
                if any(k in col.lower() for k in ["data_usage", "call_duration", "minutes"]):
                    if df[col].dtype in [np.float64, np.int64]:
                        neg = df[col] < 0
                        if int(neg.sum()) > 0:
                            df.loc[neg, col] = np.nan
                            self.log(f"  [Telecom] Nullified {int(neg.sum())} negative usage values in '{col}'")

        return df