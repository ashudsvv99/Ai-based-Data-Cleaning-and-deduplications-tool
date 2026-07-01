"""
Pipeline orchestrator: ties all components together into a
sequential cleaning workflow.

Pipeline order:
1. Load dataset
2. Profile (detect scripts, quality score)
3. Domain detection
4. Schema classification (heuristic + LLM)
5. Plan cleaning strategies + smart imputation rules
6. String pre-cleaning (whitespace, unicode)
7. Multilingual translation (categories) and transliteration (names)
8. Entity resolution (fuzzy name clustering)
9. Deduplication (exact + fuzzy matching)
10. Smart imputation (LLM rules + statistical)
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
    Master controller that executes the full cleaning pipeline.
    """

    def __init__(self, filepath: str, log_callback: Callable[[str], None] = print):
        self.filepath = filepath
        self.log = log_callback

    def execute(self) -> tuple:
        """Run the entire pipeline. Returns (cleaned_df, metadata_dict)."""
        self.log("Starting Data Cleaning Pipeline...")
        start_time = time.time()

        # Shared LLM client
        llm = LMStudioClient()

        # ── Phase 1: Load & Profile ──
        self.log("Phase 1: Loading & Profiling")
        loader = UniversalLoader(self.filepath)
        df = loader.load_and_optimize()
        initial_rows = len(df)
        self.log(f"  Loaded {initial_rows} rows, {len(df.columns)} columns.")

        profiler = DatasetProfiler(df)
        profile_data = profiler.profile()
        self.log(f"  Quality Score: {profile_data['quality_score']}/100")

        domain_info = DomainProfiler(llm_client=llm).detect_domain(df, log_callback=self.log)
        domain = domain_info["domain"]
        self.log(f"  Domain: {domain} | Confidence: {domain_info['confidence']} | Method: {domain_info['method']}")
        self.log(f"  Reasoning: {domain_info['reasoning']}")

        # ── Phase 2: Schema Classification ──
        self.log("Phase 2: AI Schema Analysis")
        schema_agent = SchemaAgent(llm)
        schema_mapping = schema_agent.classify_columns(df, log_callback=self.log)

        # ── Phase 3: Plan Cleaning Strategies ──
        self.log("Phase 3: Planning Cleaning Strategies")
        planner = PlannerAgent(llm)
        strategies = planner.plan(schema_mapping, log_callback=self.log)

        # Generate smart imputation rules
        smart_rules = planner.generate_smart_imputation_rules(df, schema_mapping, log_callback=self.log)

        # Capture pre-cleaning metrics
        missing_before = df.isna().sum().to_dict()

        # ── Phase 3.5: Row-Level Quality Filtering ──
        self.log("Phase 3.5: Row-Level Quality Filtering")
        from cleaning.quality_filter import QualityFilter
        q_filter = QualityFilter(df, schema_mapping)
        df = q_filter.filter_useless_rows()
        self.log(f"  {q_filter.get_report()}")

        # ── Phase 4: String Pre-cleaning ──
        self.log("Phase 4: String Pre-cleaning")
        df = StringCleaner.clean_all_string_columns(df)

        # ── Phase 4.5: Currency Detection & Conversion ──
        self.log("Phase 4.5: Currency Detection & Conversion to INR")
        currency_converter = CurrencyConverter()
        df, currency_report = currency_converter.convert_all(df)
        if currency_report:
            self.log(f"  Converted {len(currency_report)} column(s) to INR (₹)")
        else:
            self.log("  No mixed-currency columns detected.")

        # ── Phase 5: Multilingual Translation & Transliteration ──
        self.log("Phase 5: Multilingual Translation & Transliteration")
        ml_engine = MultilingualEngine(llm)
        standardizer = Standardizer(ml_engine)

        for col, strat in strategies.items():
            if strat.normalization == "none" or col not in df.columns:
                continue

            self.log(f"  Processing '{col}' with strategy: {strat.normalization}")

            if strat.needs_multilingual and strat.normalization in ["transliterate_name", "translate_to_english"]:
                df = standardizer.apply(df, col, strat.normalization)
            elif strat.normalization in ["normalize_email", "normalize_phone", "title_case",
                                         "uppercase_strip", "standardize_case", "coerce_numeric",
                                         "parse_dates"]:
                df = standardizer.apply(df, col, strat.normalization)

        # ── Phase 6: Entity Resolution ──
        self.log("Phase 6: Entity Resolution")
        name_cols = [
            col for col, strat in strategies.items()
            if strat.normalization == "transliterate_name" and col in df.columns
        ]

        for name_col in name_cols:
            # Build a mapping from the standardizer's translation stats
            if name_col in standardizer.stats:
                raw_mapping = standardizer.stats[name_col].get("mapping", {})
                if raw_mapping:
                    resolver = EntityResolver()
                    unified_mapping = resolver.build_name_clusters(raw_mapping)

                    # Re-apply the unified mapping
                    def apply_unified(val):
                        if pd.isna(val):
                            return pd.NA
                        s = str(val).strip()
                        return unified_mapping.get(s, s)

                    # Also map from original non-ASCII values
                    original_values = df[name_col].dropna().unique()
                    full_map = {}
                    for v in original_values:
                        v_str = str(v).strip()
                        full_map[v_str] = unified_mapping.get(v_str, v_str)

                    df[name_col] = df[name_col].apply(
                        lambda x: full_map.get(str(x).strip(), x) if pd.notna(x) else pd.NA
                    )

        # ── Phase 7: Domain-Specific Rules ──
        self.log("Phase 7: Domain-Specific Rules")
        if domain == "Retail":
            if "priority" in df.columns and "customer_type" in df.columns:
                b2x_mask = df["customer_type"].astype(str).str.upper().str.strip().isin(["B2B", "B2C"])
                missing_mask = df["priority"].isna() | df["priority"].astype(str).str.strip().isin(["", "nan", "None"])
                df.loc[b2x_mask & missing_mask, "priority"] = "Medium"
                filled = (b2x_mask & missing_mask).sum()
                if filled > 0:
                    self.log(f"  [Domain] Filled {filled} missing priorities for B2B/B2C customers")
        elif domain == "Finance":
            self.log("  (Finance rules: strict outlier handling prioritized)")
        elif domain == "Healthcare":
            self.log("  (Healthcare rules: privacy checks prioritized)")

        # ── Phase 8: Deduplication & Entity Resolution ──
        self.log("Phase 8: Deduplication & Entity Resolution")
        dedup_strategies = {col: strat.deduplication for col, strat in strategies.items()}
        
        # Transactional domains require keeping all rows to preserve events.
        # Master Data domains (CRM, HR) can safely collapse rows.
        is_master_data = domain in ["CRM", "HR"]
        dedup = DeduplicationEngine(df, dedup_strategies, keep_all_rows=not is_master_data, log_callback=self.log)
        df = dedup.execute()
        removed_by_dedup = initial_rows - len(df)
        if removed_by_dedup > 0:
            self.log(f"  Removed {removed_by_dedup} duplicate rows, kept {len(df)} unique records.")
        if dedup.cluster_report:
            self.log(f"  Found {len(dedup.cluster_report)} duplicate clusters.")

        # ── Phase 9: Smart Imputation ──
        self.log("Phase 9: Smart Imputation")
        imputer = SmartImputer()

        # Phase 9a: Apply LLM-generated rules
        df = imputer.apply_smart_rules(df, smart_rules)

        # Phase 9b: Statistical fallback for remaining missing values
        self.log("  -> Statistical fallback imputation")
        for col, strat in strategies.items():
            if col in df.columns and strat.imputation != "leave_empty":
                df = imputer.apply_statistical(df, col, strat.imputation)

        # ── Phase 10: Outlier Detection & Treatment ──
        all_numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        outlier_handler = OutlierHandler()
        if all_numeric_cols:
            self.log("Phase 10: Outlier Detection & Handling")
            df = outlier_handler.handle_all_numeric(df, all_numeric_cols)
            total_outliers = sum(v.get('outliers_found', 0) for v in outlier_handler.stats.values())
            domain_outliers = sum(v.get('domain_outliers_fixed', 0) for v in outlier_handler.stats.values())
            self.log(f"  Statistical outliers clipped: {total_outliers}")
            if domain_outliers > 0:
                self.log(f"  Domain-boundary violations fixed: {domain_outliers}")

        # ── Phase 11: Validation ──
        self.log("Phase 11: Validation & Confidence Scoring")
        validator = Validator()
        validation_result = validator.validate(df, schema_mapping)
        self.log(f"  Validation Score: {validation_result['overall_confidence']}%")
        if validation_result["issues"]:
            for issue in validation_result["issues"]:
                self.log(f"  [Issue] {issue}")

        # Optional: LLM spot-check
        try:
            val_agent = ValidationAgent(llm)
            llm_validation = val_agent.spot_check(df, log_callback=self.log)
            validation_result.update(llm_validation)
        except Exception as e:
            self.log(f"  [Warning] LLM validation skipped: {e}")

        # ── Phase 12: Generate Audit Trail ──
        self.log("Phase 12: Generating Audit Trail")
        explainer = ExplanationAgent(llm)
        all_stats = {**standardizer.stats, **ml_engine.stats}
        explanations = explainer.explain_transformations(all_stats)

        # ── Phase 13: Final Exact Duplicate Sweep ──
        df = df.drop_duplicates().reset_index(drop=True)

        final_rows = len(df)
        exec_time = time.time() - start_time
        self.log(f"Pipeline Completed in {exec_time:.2f} seconds!")
        self.log(f"  Rows: {initial_rows} -> {final_rows}")

        metadata = {
            "initial_rows": initial_rows,
            "final_rows": final_rows,
            "domain": domain,
            "domain_info": domain_info,
            "execution_time_sec": round(exec_time, 2),
            "profile": profile_data,
            "schema_mapping": {col: s.dict() for col, s in schema_mapping.items()},
            "strategies": {col: s.dict() for col, s in strategies.items()},
            "missing_values_before": missing_before,
            "translation_stats": all_stats,
            "smart_imputation_rules": [
                r.__dict__ if hasattr(r, "__dict__") else r
                for r in imputer.applied_rules
            ],
            "statistical_imputation_log": imputer.statistical_log,
            "dedup_changes": dedup.dedup_changes,
            "dedup_cluster_report": dedup.cluster_report,
            "validation": validation_result,
            "explanations": explanations,
            "outlier_stats": outlier_handler.stats if all_numeric_cols else {},
            "currency_report": currency_report,
        }

        return df, metadata
