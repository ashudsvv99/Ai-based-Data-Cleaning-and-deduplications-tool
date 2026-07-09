"""
LLM-assisted schema agent.

Three-pass column classification:
1. Heuristic pass  — fast, reliable, no LLM. Classifies semantic type.
2. LLM pass        — only for columns with heuristic confidence < 0.80.
3. LLM imputation  — LLM inspects each column's actual distribution
                     (missing %, skew, unique ratio) and picks the best
                     imputation method with reasoning.

Intent-Aware Constraints (enforced AFTER LLM runs):
  Non-Predictive Business:
    - Critical business columns (Name, Email, Phone, ID_Code, Location, Temporal)
      MUST use leave_empty — never statistically fabricate business identity data.
  Predictive:
    - Target variables MUST use leave_empty — rows with missing targets are dropped.
    - Time-series numeric columns default to fill_forward before LLM overrides.
"""
import json
import pandas as pd
import numpy as np
from typing import Dict, List
from pydantic import BaseModel, Field
from agents.llm_client import LMStudioClient
from backend.schema_detector import classify_all_columns


class ColumnSchema(BaseModel):
    semantic_type: str = Field(
        description=(
            "One of: Name, Email, Phone, Location, ID_Code, Numeric, Temporal, "
            "Categorical, Free_Text, Binary_Flag, Score_Rating, Percentage, URL, JSON_Field"
        )
    )
    imputation_strategy: str = Field(default="leave_empty")
    imputation_reasoning: str = Field(default="")
    needs_multilingual: bool = Field(default=False)
    non_ascii_ratio: float = Field(default=0.0)
    description: str = Field(default="Heuristic classification")
    is_critical_business: bool = Field(default=False)  # Non-Predictive: do NOT impute
    is_target: bool = Field(default=False)              # Predictive: drop row if missing


class SchemaAgent:
    """
    Three-pass schema classifier:
    1. Heuristic (fast, no LLM)
    2. LLM refinement for ambiguous columns
    3. LLM-chosen imputation method per column
    """

    def __init__(self, llm_client: LMStudioClient = None):
        self.llm_client = llm_client or LMStudioClient()

    # ────────────────────────────────────────────
    # Main entry point
    # ────────────────────────────────────────────
    def classify_columns(
        self,
        df: pd.DataFrame,
        log_callback=print,
        dataset_intent: str = "Non-Predictive Business",
        target_variables: List[str] = None,
        is_time_series: bool = False,
    ) -> Dict[str, ColumnSchema]:
        """
        Full three-pass classification.

        Parameters
        ----------
        dataset_intent   : "Predictive" | "Non-Predictive Business"
        target_variables : list of column names that are ML targets (Predictive only)
        is_time_series   : if True, numeric columns default to fill_forward
        """
        target_variables = target_variables or []

        # ── Pass 1: Heuristic ──
        log_callback("SchemaAgent: Pass 1 — Heuristic classification...")
        heuristic_results = classify_all_columns(df)

        schema: Dict[str, ColumnSchema] = {}
        ambiguous_cols = []

        # Semantic types that are critical business identity columns.
        # For Non-Predictive Business, Categorical status/tier/type should also
        # use leave_empty rather than mode-filling (status = 'Active' is not safe to assume).
        _CRITICAL_TYPES = {"Name", "Email", "Phone", "ID_Code", "Location", "Temporal", "URL", "JSON_Field"}

        for col, info in heuristic_results.items():
            sem_type   = info["semantic_type"]
            confidence = info["confidence"]
            needs_ml   = info["needs_multilingual"]

            is_critical = dataset_intent == "Non-Predictive Business" and sem_type in _CRITICAL_TYPES
            is_target   = col in target_variables

            # Default imputation — will be refined by LLM in Pass 3
            if is_critical or is_target:
                default_strat = "leave_empty"
            elif is_time_series and sem_type == "Numeric":
                default_strat = "fill_forward"
            else:
                default_strat = self._default_imputation(sem_type)

            schema[col] = ColumnSchema(
                semantic_type=sem_type,
                imputation_strategy=default_strat,
                needs_multilingual=needs_ml,
                non_ascii_ratio=info["non_ascii_ratio"],
                description=f"Heuristic ({confidence:.0%} confidence)",
                is_critical_business=is_critical,
                is_target=is_target,
            )
            if confidence < 0.80:
                ambiguous_cols.append(col)

        # ── Pass 2: LLM for ambiguous columns ──
        if ambiguous_cols:
            log_callback(f"SchemaAgent: Pass 2 — LLM refinement for {len(ambiguous_cols)} ambiguous columns...")
            llm_schema = self._llm_classify(df, ambiguous_cols, dataset_intent)
            for col, llm_info in llm_schema.items():
                if col in schema and isinstance(llm_info, dict):
                    schema[col].semantic_type = llm_info.get("semantic_type", schema[col].semantic_type)
                    schema[col].description   = "LLM classification"
                    # Re-evaluate critical flag after semantic type override
                    schema[col].is_critical_business = (
                        dataset_intent == "Non-Predictive Business"
                        and schema[col].semantic_type in _CRITICAL_TYPES
                    )
            # Re-check multilingual after override
            for col in ambiguous_cols:
                if col in schema:
                    schema[col].needs_multilingual = heuristic_results.get(col, {}).get("non_ascii_ratio", 0) > 0.01

        # ── Pass 3: LLM-chosen imputation ──
        log_callback("SchemaAgent: Pass 3 — LLM imputation strategy selection...")
        self._llm_choose_imputation(df, schema, dataset_intent, is_time_series)

        # ── Post-LLM: enforce intent constraints ──────────────────
        log_callback("SchemaAgent: Enforcing intent-aware imputation constraints...")
        _STATISTICAL = {"fill_mean", "fill_median", "fill_mode", "fill_knn"}
        for col, s in schema.items():
            if s.is_critical_business and s.imputation_strategy in _STATISTICAL:
                s.imputation_strategy  = "leave_empty"
                s.imputation_reasoning = (
                    f"[Non-Predictive Business] Critical business column '{col}' ({s.semantic_type}) — "
                    "statistical fabrication is not allowed. Kept as empty/null."
                )
            if s.is_target and s.imputation_strategy in _STATISTICAL:
                s.imputation_strategy  = "leave_empty"
                s.imputation_reasoning = (
                    f"[Predictive] Target variable '{col}' — rows with missing targets "
                    "will be dropped by the pipeline, not imputed."
                )

        # Print summary
        for col, s in schema.items():
            ml_flag  = " [MULTILINGUAL]" if s.needs_multilingual else ""
            crit_flag = " [CRITICAL]" if s.is_critical_business else ""
            tgt_flag  = " [TARGET]"  if s.is_target else ""
            log_callback(f"  -> {col}: {s.semantic_type} | impute={s.imputation_strategy}{ml_flag}{crit_flag}{tgt_flag}")
            if s.imputation_reasoning:
                log_callback(f"       Reason: {s.imputation_reasoning}")

        return schema

    # ────────────────────────────────────────────
    # Pass 2: LLM semantic type classifier
    # ────────────────────────────────────────────
    def _llm_classify(
        self,
        df: pd.DataFrame,
        columns: list,
        dataset_intent: str = "",
        domain: str = "Generic",
    ) -> dict:
        sample_data = df[columns].head(5).to_dict(orient="records")
        intent_hint = f"Dataset intent: {dataset_intent}. Domain: {domain}." if dataset_intent else ""
        system_prompt = (
            "You are an expert Data Engineer. Classify each column into EXACTLY ONE semantic type.\n\n"
            "Available types:\n"
            "  Name         — Person or company name\n"
            "  Email        — Email address\n"
            "  Phone        — Phone / mobile number\n"
            "  Location     — City, state, country, address, pincode\n"
            "  ID_Code      — Unique identifier, account number, reference code\n"
            "  Numeric      — Continuous number (age, salary, amount, price, quantity)\n"
            "  Temporal     — Date, time, timestamp, datetime\n"
            "  Categorical  — Limited set of distinct categories (status, type, gender, priority)\n"
            "  Binary_Flag  — Binary 0/1, True/False, Yes/No columns (churn, fraud, is_active)\n"
            "  Score_Rating — Numeric score or rating (credit_score, nps, review_rating, risk_score)\n"
            "  Percentage   — Values representing percentages (discount_pct, completion_rate)\n"
            "  URL          — Web URLs or links\n"
            "  JSON_Field   — JSON/dict stored as string\n"
            "  Free_Text    — Open-ended text (comments, notes, description)\n\n"
            f"{intent_hint}\n\n"
            "Return ONLY a JSON object where each key is a column name and the value is:\n"
            '{"semantic_type": "<type>"}\n\n'
            "EXAMPLES:\n"
            '{"full_name": {"semantic_type": "Name"}, '
            '"order_status": {"semantic_type": "Categorical"}, '
            '"churn": {"semantic_type": "Binary_Flag"}, '
            '"credit_score": {"semantic_type": "Score_Rating"}, '
            '"discount_pct": {"semantic_type": "Percentage"}}'
        )
        user_prompt = (
            f"Columns: {json.dumps(columns)}\n"
            f"Sample data:\n{json.dumps(sample_data, ensure_ascii=False, default=str)}\n\n"
            "OUTPUT JSON:"
        )
        result = self.llm_client.chat_completion_json(
            system_prompt, user_prompt, num_expected_keys=len(columns), enable_thinking=True
        )
        return result if isinstance(result, dict) else {}

    # ────────────────────────────────────────────
    # Pass 3: LLM imputation strategy chooser
    # ────────────────────────────────────────────
    def _llm_choose_imputation(
        self,
        df: pd.DataFrame,
        schema: Dict[str, ColumnSchema],
        dataset_intent: str = "",
        is_time_series: bool = False,
    ) -> None:
        """
        For every column that has missing values, build a rich statistical
        profile and ask the LLM to pick the best imputation strategy.
        Updates schema in-place.
        """
        columns_with_missing = []

        for col, col_schema in schema.items():
            if col not in df.columns:
                continue
            series = df[col]
            missing_count = int(series.isna().sum())
            if missing_count == 0:
                continue   # no missing values → keep default

            total = len(series)
            missing_pct = round(missing_count / total * 100, 1)

            stat = {
                "column": col,
                "semantic_type": col_schema.semantic_type,
                "missing_count": missing_count,
                "missing_pct": missing_pct,
                "total_rows": total,
                "unique_values": int(series.nunique()),
            }

            # Numeric distribution stats
            if pd.api.types.is_numeric_dtype(series):
                non_null = series.dropna()
                if len(non_null) > 0:
                    stat["mean"]   = round(float(non_null.mean()), 4)
                    stat["median"] = round(float(non_null.median()), 4)
                    stat["std"]    = round(float(non_null.std()), 4)
                    # Skewness — positive = right-skewed → prefer median
                    stat["skewness"] = round(float(non_null.skew()), 3)

            # Categorical: top values
            elif pd.api.types.is_object_dtype(series):
                top = series.dropna().value_counts().head(5)
                stat["top_values"] = top.to_dict()
                stat["top_value_coverage_pct"] = round(
                    float(top.sum()) / max(total - missing_count, 1) * 100, 1
                )

            columns_with_missing.append(stat)

        if not columns_with_missing:
            print("  SchemaAgent: No columns with missing values — skipping LLM imputation selection.")
            return

        # Build prompt — send all missing columns in one call
        intent_rules = ""
        if dataset_intent == "Non-Predictive Business":
            intent_rules = (
                "\nCRITICAL RULES for Non-Predictive Business datasets:\n"
                "  - Name, Email, Phone, ID_Code, Location, Temporal columns → MUST use leave_empty.\n"
                "  - Never fabricate or statistically infer business identity data.\n"
            )
        elif dataset_intent == "Predictive":
            intent_rules = (
                "\nCRITICAL RULES for Predictive datasets:\n"
                "  - Target/label columns → MUST use leave_empty (rows will be dropped).\n"
            )
            if is_time_series:
                intent_rules += (
                    "  - Time-series numeric columns → prefer fill_forward or fill_backward.\n"
                )

        system_prompt = (
            "You are an expert Data Scientist specializing in missing value imputation.\n"
            "For each column described below, choose the BEST imputation strategy.\n"
            f"{intent_rules}\n"
            "Available strategies:\n"
            "  fill_mean        — normally distributed numeric columns\n"
            "  fill_median      — skewed numeric columns or when outliers exist (PREFERRED for financial/medical data)\n"
            "  fill_mode        — categorical, low-cardinality, or heavily repeated values\n"
            "  fill_forward     — time-series ordered numeric data (propagate last known value forward)\n"
            "  fill_backward    — time-series ordered data (propagate next known value backward)\n"
            "  fill_interpolate — time-series continuous data (linear interpolation between known points)\n"
            "  fill_knn         — numeric columns where neighboring records give context (small-medium datasets)\n"
            "  leave_empty      — IDs, names, URLs, free text, targets, or when imputation would be fabrication\n\n"
            "DOMAIN-SPECIFIC GUIDANCE:\n"
            "  Healthcare: age/vitals → fill_median; diagnosis/MRN → leave_empty\n"
            "  Finance: amount/balance → fill_median; risk_score/account_id → leave_empty\n"
            "  HR: department → fill_mode; salary → leave_empty; attendance_pct → fill_median\n"
            "  Retail: priority/status → fill_mode; price → fill_median; customer_id → leave_empty\n"
            "  IoT/Time-series: sensor readings → fill_interpolate; device_id → leave_empty\n\n"
            "Return ONLY a JSON object where each key is the column name and value is:\n"
            '{"strategy": "<strategy>", "reasoning": "<one sentence>"}\n\n'
            "EXAMPLES:\n"
            '{"age": {"strategy": "fill_median", "reasoning": "Age is right-skewed in patient data; median avoids outlier bias."},\n'
            ' "order_status": {"strategy": "fill_mode", "reasoning": "Low-cardinality status field; mode fills the most common operational state."},\n'
            ' "temperature": {"strategy": "fill_interpolate", "reasoning": "Sensor data is time-ordered; interpolation is more accurate than propagation."},\n'
            ' "churn": {"strategy": "leave_empty", "reasoning": "Target variable — rows with missing targets will be dropped by the pipeline."}}'
        )

        user_prompt = (
            f"Columns with missing values:\n"
            f"{json.dumps(columns_with_missing, ensure_ascii=False, default=str)}\n\n"
            "OUTPUT JSON:"
        )

        result = self.llm_client.chat_completion_json(
            system_prompt, user_prompt,
            num_expected_keys=len(columns_with_missing),
            enable_thinking=True
        )

        if not isinstance(result, dict):
            print("  SchemaAgent: LLM imputation selection returned unexpected format. Keeping defaults.")
            return

        valid_strategies = {
            "fill_mean", "fill_median", "fill_mode",
            "fill_forward", "fill_backward", "fill_knn",
            "fill_interpolate", "leave_empty",
        }
        for col, info in result.items():
            if col in schema and isinstance(info, dict):
                strategy  = str(info.get("strategy", "")).strip().lower()
                reasoning = str(info.get("reasoning", "")).strip()
                # Do not override leave_empty for critical/target columns
                if schema[col].is_critical_business or schema[col].is_target:
                    print(f"  [Imputation] '{col}' → leave_empty (intent constraint — LLM suggestion '{strategy}' ignored)")
                    continue
                if strategy in valid_strategies:
                    schema[col].imputation_strategy  = strategy
                    schema[col].imputation_reasoning = reasoning
                    print(f"  [Imputation] '{col}' → {strategy} | {reasoning}")

    # ────────────────────────────────────────────
    # Fallback defaults (used before LLM runs)
    # ────────────────────────────────────────────
    @staticmethod
    def _default_imputation(semantic_type: str) -> str:
        """Rule-based fallback imputation before LLM runs."""
        defaults = {
            "Numeric":      "fill_median",
            "Categorical":  "fill_mode",
            "Name":         "leave_empty",
            "Email":        "leave_empty",
            "Phone":        "leave_empty",
            "Location":     "fill_mode",
            "ID_Code":      "leave_empty",
            "Temporal":     "leave_empty",
            "Free_Text":    "leave_empty",
            "Binary_Flag":  "fill_mode",
            "Score_Rating": "fill_median",
            "Percentage":   "fill_median",
            "URL":          "leave_empty",
            "JSON_Field":   "leave_empty",
        }
        return defaults.get(semantic_type, "leave_empty")
