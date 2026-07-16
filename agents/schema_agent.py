"""
LLM-assisted schema agent — Domain-Aware, Context-Rich Classification.

Three-pass column classification:
  Pass 1: Heuristic  — fast, reliable, no LLM. Classifies semantic type using
           column name patterns, dtype, cardinality, and non-ASCII ratios.
  Pass 2: LLM pass  — for ALL columns with heuristic confidence < 0.85.
           Now receives: domain, domain_reasoning, full column profiles
           (dtype, missing%, unique count, sample values, non-ASCII, scripts)
           so it can make domain-aware decisions.
           Example: in a Healthcare dataset, "code" → ID_Code (not Categorical).
  Pass 3: LLM imputation — inspects each column's actual distribution
           (missing%, skew, unique ratio) and picks the best imputation
           method with reasoning, using domain context.

New Semantic Types:
  Geospatial   — lat/lon coordinate pairs
  Currency     — values with currency symbols (₹, $, €, £, ¥)
  Structured_ID — pattern-matching IDs (SSN, passport, IFSC, PAN, Aadhaar)

Intent-Aware Constraints (enforced AFTER LLM runs):
  Non-Predictive Business:
    - Critical business columns MUST use fill_none — converts sentinel strings
      to None/NaN. Never statistically fabricate business identity data.
  Predictive:
    - Target variables MUST use leave_empty — rows with missing targets are dropped.
    - Time-series numeric columns default to fill_forward before LLM overrides.

LLM Fallback:
    If LM Studio is unreachable or returns invalid JSON:
    - Pass 2: column keeps its heuristic classification.
    - Pass 3: column keeps its heuristic default strategy.
    - WARNING is printed so the operator knows LLM was bypassed.
    - All business-safety constraints (fill_none guards) still apply.
"""
import json
import re
import pandas as pd
import numpy as np
from typing import Dict, List
from pydantic import BaseModel, Field
from agents.llm_client import LMStudioClient
from backend.schema_detector import classify_all_columns, column_non_ascii_ratio, column_script_distribution


class ColumnSchema(BaseModel):
    semantic_type: str = Field(
        description=(
            "One of: Name, Email, Phone, Location, ID_Code, Structured_ID, Numeric, Temporal, "
            "Categorical, Free_Text, Binary_Flag, Score_Rating, Percentage, URL, JSON_Field, "
            "Geospatial, Currency"
        )
    )
    imputation_strategy: str = Field(default="leave_empty")
    imputation_reasoning: str = Field(default="")
    needs_multilingual: bool = Field(default=False)
    non_ascii_ratio: float = Field(default=0.0)
    description: str = Field(default="Heuristic classification")
    is_critical_business: bool = Field(default=False)  # Non-Predictive: do NOT impute
    is_target: bool = Field(default=False)             # Predictive: drop row if missing


class SchemaAgent:
    """
    Three-pass schema classifier — domain-aware and context-rich.
      Pass 1: Heuristic (fast, no LLM)
      Pass 2: LLM refinement — ambiguous columns get domain context + full profiles
      Pass 3: LLM-chosen imputation method per column
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
        domain: str = "Generic",
        domain_reasoning: str = "",
        has_multilingual_data: bool = False,
    ) -> Dict[str, ColumnSchema]:
        """
        Full three-pass classification with domain awareness.

        Parameters
        ----------
        dataset_intent      : "Predictive" | "Non-Predictive Business"
        target_variables    : list of column names that are ML targets (Predictive only)
        is_time_series      : if True, numeric columns default to fill_forward
        domain              : detected domain (e.g. "Healthcare", "Retail")
        domain_reasoning    : LLM's reasoning about the domain (gives schema agent more context)
        has_multilingual_data: True if domain profiler detected non-ASCII content
        """
        target_variables = target_variables or []

        # ── Pass 1: Heuristic ──
        log_callback(f"SchemaAgent: Pass 1 — Heuristic classification (domain={domain})...")
        heuristic_results = classify_all_columns(df)

        # Also run enhanced pattern detectors for new types
        enhanced_types = self._enhanced_type_detection(df)

        schema: Dict[str, ColumnSchema] = {}
        ambiguous_cols = []

        _CRITICAL_TYPES = {
            "Name", "Email", "Phone", "ID_Code", "Structured_ID", "Location", "Temporal",
            "URL", "JSON_Field", "Financial", "Currency",
        }

        _SENSITIVE_PATTERNS = [
            "salary", "wage", "wages", "income", "pay", "compensation",
            "bonus", "ctc", "package", "remuneration", "stipend",
            "payment_method", "payment_mode", "pay_method", "pay_mode",
            "mode_of_payment", "payment_type", "pay_type",
            "bank_account", "bank_no", "routing", "ifsc", "swift", "iban",
            "credit_card", "card_number", "card_no", "cvv",
            "dob", "date_of_birth", "birth_date", "birthdate",
            "gender", "sex",
            "marital_status", "marital", "religion", "caste", "ethnicity", "race",
        ]

        # Threshold: stricter in well-known domains (LLM context helps more),
        # looser in Generic where ambiguity is higher.
        confidence_threshold = 0.75 if domain == "Generic" else 0.85

        for col, info in heuristic_results.items():
            sem_type   = info["semantic_type"]
            confidence = info["confidence"]
            needs_ml   = info["needs_multilingual"]

            # Override with enhanced detection if it found a more specific type
            if col in enhanced_types:
                sem_type   = enhanced_types[col]
                confidence = 0.92  # High confidence from pattern matching
                needs_ml   = False

            is_critical = dataset_intent == "Non-Predictive Business" and sem_type in _CRITICAL_TYPES
            is_target   = col in target_variables

            col_lower = col.lower().replace(" ", "_")
            is_name_sensitive = (
                dataset_intent == "Non-Predictive Business"
                and any(pat in col_lower for pat in _SENSITIVE_PATTERNS)
            )
            if is_name_sensitive:
                is_critical = True

            # Default imputation
            if is_critical or is_target:
                default_strat = "fill_none"
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

            if confidence < confidence_threshold:
                ambiguous_cols.append(col)

        # ── Pass 2: LLM for ambiguous columns — domain-aware ──
        if ambiguous_cols:
            log_callback(
                f"SchemaAgent: Pass 2 — LLM refinement for {len(ambiguous_cols)} ambiguous columns "
                f"(domain context: {domain})..."
            )
            col_profiles = self._build_column_profiles(df, ambiguous_cols)
            llm_schema = self._llm_classify(
                df, ambiguous_cols, dataset_intent, domain, domain_reasoning, col_profiles
            )
            if not llm_schema:
                log_callback(
                    f"  [WARNING] SchemaAgent Pass 2: LLM returned empty response "
                    f"(LM Studio offline or timeout). Keeping heuristic types for: {ambiguous_cols}"
                )
            for col, llm_info in llm_schema.items():
                if col in schema and isinstance(llm_info, dict):
                    new_type = llm_info.get("semantic_type", schema[col].semantic_type)
                    schema[col].semantic_type = new_type
                    schema[col].description   = (
                        f"LLM [{domain}] classification"
                        + (f" | {llm_info.get('reasoning', '')[:80]}" if llm_info.get('reasoning') else "")
                    )
                    # Re-evaluate critical flag after semantic type override
                    schema[col].is_critical_business = (
                        dataset_intent == "Non-Predictive Business"
                        and schema[col].semantic_type in _CRITICAL_TYPES
                    )
            # Re-check multilingual after override
            for col in ambiguous_cols:
                if col in schema:
                    schema[col].needs_multilingual = (
                        heuristic_results.get(col, {}).get("non_ascii_ratio", 0) > 0.01
                    )

        # ── Pass 3: LLM-chosen imputation ──
        log_callback("SchemaAgent: Pass 3 — LLM imputation strategy selection...")
        self._llm_choose_imputation(df, schema, dataset_intent, is_time_series, domain)

        # ── Post-LLM: enforce intent constraints ──
        log_callback("SchemaAgent: Enforcing intent-aware imputation constraints...")
        _STATISTICAL = {"fill_mean", "fill_median", "fill_mode", "fill_knn",
                        "fill_forward", "fill_backward", "fill_interpolate"}
        for col, s in schema.items():
            if s.is_critical_business and s.imputation_strategy in _STATISTICAL:
                s.imputation_strategy  = "fill_none"
                s.imputation_reasoning = (
                    f"[Non-Predictive Business] Business-sensitive column '{col}' ({s.semantic_type}) — "
                    "statistical imputation not allowed. Sentinel strings → None/NaN only."
                )
            if s.is_target and s.imputation_strategy in _STATISTICAL:
                s.imputation_strategy  = "leave_empty"
                s.imputation_reasoning = (
                    f"[Predictive] Target variable '{col}' — rows with missing targets "
                    "will be dropped by the pipeline, not imputed."
                )

        # Print summary
        log_callback(f"\nSchemaAgent: Classification Summary ({len(schema)} columns):")
        for col, s in schema.items():
            ml_flag   = " [MULTILINGUAL]" if s.needs_multilingual else ""
            crit_flag = " [CRITICAL]"     if s.is_critical_business else ""
            tgt_flag  = " [TARGET]"       if s.is_target else ""
            log_callback(
                f"  -> {col}: {s.semantic_type} | impute={s.imputation_strategy}"
                f"{ml_flag}{crit_flag}{tgt_flag}"
            )
            if s.imputation_reasoning:
                log_callback(f"       Reason: {s.imputation_reasoning}")

        return schema

    # ────────────────────────────────────────────
    # Enhanced pattern-based type detection
    # ────────────────────────────────────────────
    def _enhanced_type_detection(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Detect specialized semantic types using regex patterns:
        - Geospatial (lat/lon columns or coordinate-looking numeric pairs)
        - Currency (values with ₹, $, €, £, ¥ symbols)
        - Structured_ID (PAN, Aadhaar, SSN, IFSC, passport patterns)
        """
        enhanced = {}
        cols_lower = {col: col.lower().replace(" ", "_") for col in df.columns}

        # Geospatial detection
        lat_hints  = ["latitude", "lat", "latitude_deg"]
        lon_hints  = ["longitude", "lon", "lng", "longitude_deg"]
        for col, col_l in cols_lower.items():
            if any(h in col_l for h in lat_hints):
                enhanced[col] = "Geospatial"
            elif any(h in col_l for h in lon_hints):
                enhanced[col] = "Geospatial"

        # Currency detection — look for currency symbols in string columns
        currency_pattern = re.compile(r'[₹$€£¥₩₪₫฿₨]')
        for col in df.columns:
            if col in enhanced:
                continue
            if pd.api.types.is_object_dtype(df[col]):
                sample = df[col].dropna().astype(str).head(50)
                currency_hits = sample.str.contains(currency_pattern, regex=True).sum()
                if currency_hits > len(sample) * 0.3:  # >30% of values have currency symbol
                    enhanced[col] = "Currency"

        # Structured_ID detection — regex patterns for common ID formats
        structured_id_patterns = {
            "pan":     re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$'),           # PAN card
            "aadhaar": re.compile(r'^\d{4}\s?\d{4}\s?\d{4}$'),            # Aadhaar
            "ssn":     re.compile(r'^\d{3}-\d{2}-\d{4}$'),               # US SSN
            "ifsc":    re.compile(r'^[A-Z]{4}0[A-Z0-9]{6}$'),            # IFSC code
            "passport":re.compile(r'^[A-Z][0-9]{7}$'),                   # Passport
            "gstin":   re.compile(r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$'),
        }
        for col in df.columns:
            if col in enhanced:
                continue
            if pd.api.types.is_object_dtype(df[col]):
                sample = df[col].dropna().astype(str).head(50)
                for pattern_name, pattern in structured_id_patterns.items():
                    matches = sample.str.match(pattern).sum()
                    if matches > len(sample) * 0.5:  # >50% match
                        enhanced[col] = "Structured_ID"
                        break

        return enhanced

    # ────────────────────────────────────────────
    # Pass 2: LLM semantic type classifier (domain-aware)
    # ────────────────────────────────────────────
    def _llm_classify(
        self,
        df: pd.DataFrame,
        columns: list,
        dataset_intent: str = "",
        domain: str = "Generic",
        domain_reasoning: str = "",
        col_profiles: dict = None,
    ) -> dict:
        """
        Domain-aware LLM column classification.
        Sends full column profiles so the LLM can make informed decisions.
        """
        col_profiles = col_profiles or {}
        intent_hint = (
            f"Dataset Domain: {domain}. "
            f"Dataset Intent: {dataset_intent}. "
            + (f"Domain context: {domain_reasoning[:150]}." if domain_reasoning else "")
        )

        system_prompt = (
            "You are an expert Data Engineer specializing in semantic column type classification.\n"
            "You know the dataset's domain — use this to make smarter decisions.\n\n"
            "SEMANTIC TYPES:\n"
            "  Name          — Person or company/organization name\n"
            "  Email         — Email address\n"
            "  Phone         — Phone / mobile / fax number\n"
            "  Location      — City, state, country, address, pincode, region\n"
            "  ID_Code       — Unique identifier, account number, reference code (generic)\n"
            "  Structured_ID — Pattern-validated ID: PAN, Aadhaar, SSN, GSTIN, IFSC, passport\n"
            "  Numeric       — Continuous number (age, salary, amount, price, quantity, count)\n"
            "  Temporal      — Date, time, timestamp, datetime\n"
            "  Categorical   — Limited set of distinct categories (status, type, gender, priority)\n"
            "  Binary_Flag   — Binary 0/1, True/False, Yes/No (churn, fraud, is_active)\n"
            "  Score_Rating  — Numeric score or rating (credit_score, nps, review_rating)\n"
            "  Percentage    — Values representing percentages (discount_pct, completion_rate)\n"
            "  Currency      — Monetary values with currency symbols (₹100, $50, €200)\n"
            "  Geospatial    — Latitude/longitude coordinates\n"
            "  URL           — Web URLs or links\n"
            "  JSON_Field    — JSON/dict stored as string\n"
            "  Free_Text     — Open-ended text (comments, notes, description)\n\n"
            "DOMAIN-AWARE RULES:\n"
            "  Healthcare: 'code' → ID_Code, 'diagnosis' → Categorical, 'glucose' → Numeric\n"
            "  HR: 'band/level' → Categorical, 'salary' → Numeric, 'department' → Categorical\n"
            "  Finance: 'account' → ID_Code, 'amount' → Currency, 'status' → Categorical\n"
            "  Retail: 'sku' → ID_Code, 'priority' → Categorical, 'quantity' → Numeric\n"
            "  Education: 'marks/gpa' → Score_Rating, 'grade' → Categorical\n\n"
            f"{intent_hint}\n\n"
            "Return ONLY a JSON object where each key is a column name and the value is:\n"
            '{"semantic_type": "<type>", "reasoning": "<one sentence>"}\n\n'
            "EXAMPLES:\n"
            '{"full_name": {"semantic_type": "Name", "reasoning": "Person name column."}, '
            '"order_status": {"semantic_type": "Categorical", "reasoning": "Limited status values."}, '
            '"churn": {"semantic_type": "Binary_Flag", "reasoning": "0/1 prediction target."}, '
            '"credit_score": {"semantic_type": "Score_Rating", "reasoning": "Numeric risk score."}, '
            '"gstin": {"semantic_type": "Structured_ID", "reasoning": "Matches GSTIN format."}}'
        )

        # Build compact profile per column for the prompt
        col_context = {}
        for col in columns:
            p = col_profiles.get(col, {})
            col_context[col] = {
                "dtype":         p.get("dtype", "unknown"),
                "missing_pct":   p.get("missing_pct", 0),
                "unique_count":  p.get("unique_count", 0),
                "sample_values": p.get("sample_values", [])[:6],
                "non_ascii_ratio": p.get("non_ascii_ratio", 0),
            }
            if p.get("scripts_detected"):
                col_context[col]["scripts"] = p["scripts_detected"]

        user_prompt = (
            f"Columns to classify: {json.dumps(columns)}\n\n"
            f"Column profiles:\n{json.dumps(col_context, ensure_ascii=False, default=str, indent=2)}\n\n"
            "OUTPUT JSON:"
        )

        result = self.llm_client.chat_completion_json(
            system_prompt, user_prompt,
            num_expected_keys=len(columns),
            enable_thinking=True,
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
        domain: str = "Generic",
    ) -> None:
        """
        For every column that has missing values, build a rich statistical
        profile and ask the LLM to pick the best imputation strategy.
        Updates schema in-place. Domain context included.
        """
        columns_with_missing = []

        for col, col_schema in schema.items():
            if col not in df.columns:
                continue
            series = df[col]
            missing_count = int(series.isna().sum())
            if missing_count == 0:
                continue

            total = len(series)
            missing_pct = round(missing_count / total * 100, 1)

            stat = {
                "column":        col,
                "semantic_type": col_schema.semantic_type,
                "missing_count": missing_count,
                "missing_pct":   missing_pct,
                "total_rows":    total,
                "unique_values": int(series.nunique()),
                "is_critical":   col_schema.is_critical_business,
                "is_target":     col_schema.is_target,
            }

            if pd.api.types.is_numeric_dtype(series):
                non_null = series.dropna()
                if len(non_null) > 0:
                    stat["mean"]     = round(float(non_null.mean()), 4)
                    stat["median"]   = round(float(non_null.median()), 4)
                    stat["std"]      = round(float(non_null.std()), 4)
                    stat["skewness"] = round(float(non_null.skew()), 3)

            elif pd.api.types.is_object_dtype(series):
                top = series.dropna().value_counts().head(5)
                stat["top_values"]             = top.to_dict()
                stat["top_value_coverage_pct"] = round(
                    float(top.sum()) / max(total - missing_count, 1) * 100, 1
                )

            columns_with_missing.append(stat)

        if not columns_with_missing:
            print("  SchemaAgent: No columns with missing values — skipping LLM imputation selection.")
            return

        intent_rules = ""
        if dataset_intent == "Non-Predictive Business":
            intent_rules = (
                "\nCRITICAL RULES for Non-Predictive Business datasets:\n"
                "  - Name, Email, Phone, ID_Code, Structured_ID, Location, Temporal, Currency columns\n"
                "    → MUST use leave_empty. Never fabricate business identity data.\n"
                "  - Categorical/Numeric analytics columns → statistical imputation IS allowed.\n"
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
            f"You are an expert Data Scientist specializing in missing value imputation.\n"
            f"Dataset Domain: {domain}. Dataset Intent: {dataset_intent}.\n"
            f"For each column, choose the BEST imputation strategy.\n"
            f"{intent_rules}\n"
            "AVAILABLE STRATEGIES:\n"
            "  fill_mean        — normally distributed numeric columns\n"
            "  fill_median      — skewed numeric columns or when outliers exist (PREFERRED for financial/medical)\n"
            "  fill_mode        — categorical, low-cardinality, or heavily repeated values\n"
            "  fill_forward     — time-series ordered data (propagate last known value forward)\n"
            "  fill_backward    — time-series ordered data (propagate next known value backward)\n"
            "  fill_interpolate — time-series continuous data (linear interpolation)\n"
            "  fill_knn         — numeric columns where neighboring records give context\n"
            "  fill_none        — standardize sentinel strings ('N/A', '-', 'unknown') → real None/NaN\n"
            "  leave_empty      — IDs, names, URLs, free text, targets, or when imputation = fabrication\n\n"
            "DOMAIN-SPECIFIC GUIDANCE:\n"
            "  Healthcare: age/vitals → fill_median; diagnosis/MRN → leave_empty\n"
            "  Finance: amount/balance → fill_median; account_id → leave_empty\n"
            "  HR: department → fill_mode; salary → leave_empty; attendance_pct → fill_median\n"
            "  Retail: priority/status → fill_mode; price → fill_median; customer_id → leave_empty\n"
            "  IoT/Time-series: sensor readings → fill_interpolate; device_id → leave_empty\n"
            "  Education: marks/gpa → fill_median; grade → fill_mode; student_id → leave_empty\n"
            "  Agriculture: yield → fill_median; crop_type → fill_mode; farm_id → leave_empty\n\n"
            "Return ONLY a JSON object where each key is the column name and value is:\n"
            '{"strategy": "<strategy>", "reasoning": "<one sentence>"}\n\n'
            "EXAMPLES:\n"
            '{"age": {"strategy": "fill_median", "reasoning": "Right-skewed; median avoids outlier bias."},\n'
            ' "order_status": {"strategy": "fill_mode", "reasoning": "Low-cardinality; mode fills most common state."},\n'
            ' "temperature": {"strategy": "fill_interpolate", "reasoning": "Sensor time-series; interpolation is most accurate."},\n'
            ' "churn": {"strategy": "leave_empty", "reasoning": "Target variable — missing rows will be dropped."}}'
        )

        user_prompt = (
            f"Columns with missing values:\n"
            f"{json.dumps(columns_with_missing, ensure_ascii=False, default=str, indent=2)}\n\n"
            "OUTPUT JSON:"
        )

        result = self.llm_client.chat_completion_json(
            system_prompt, user_prompt,
            num_expected_keys=len(columns_with_missing),
            enable_thinking=True,
        )

        if not isinstance(result, dict) or not result:
            print(
                "  [WARNING] SchemaAgent Pass 3: LLM imputation selection returned empty/invalid "
                "response. Keeping heuristic defaults."
            )
            return

        valid_strategies = {
            "fill_mean", "fill_median", "fill_mode",
            "fill_forward", "fill_backward", "fill_knn",
            "fill_interpolate", "fill_none", "leave_empty",
        }
        for col, info in result.items():
            if col in schema and isinstance(info, dict):
                strategy  = str(info.get("strategy", "")).strip().lower()
                reasoning = str(info.get("reasoning", "")).strip()
                if schema[col].is_critical_business:
                    print(f"  [Imputation] '{col}' → fill_none (business-sensitive — LLM '{strategy}' ignored)")
                    continue
                if schema[col].is_target:
                    print(f"  [Imputation] '{col}' → leave_empty (target variable — LLM '{strategy}' ignored)")
                    continue
                if strategy in valid_strategies:
                    schema[col].imputation_strategy  = strategy
                    schema[col].imputation_reasoning = reasoning
                    print(f"  [Imputation] '{col}' → {strategy} | {reasoning}")

    # ────────────────────────────────────────────
    # Column profile builder for LLM context
    # ────────────────────────────────────────────
    def _build_column_profiles(self, df: pd.DataFrame, columns: list) -> dict:
        """Build rich per-column profiles for LLM prompts."""
        profiles = {}
        for col in columns:
            if col not in df.columns:
                continue
            series = df[col]
            missing_count = int(series.isna().sum())
            total = len(series)

            profile = {
                "dtype":        str(series.dtype),
                "missing_pct":  round(missing_count / max(total, 1) * 100, 1),
                "unique_count": int(series.nunique()),
                "sample_values": [str(v) for v in series.dropna().head(8).tolist()],
            }

            if pd.api.types.is_numeric_dtype(series):
                non_null = series.dropna()
                if len(non_null) > 0:
                    profile["min"]  = round(float(non_null.min()), 3)
                    profile["max"]  = round(float(non_null.max()), 3)
                    profile["mean"] = round(float(non_null.mean()), 3)

            if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
                non_ascii = column_non_ascii_ratio(series)
                profile["non_ascii_ratio"] = round(non_ascii, 3)
                if non_ascii > 0.01:
                    profile["scripts_detected"] = column_script_distribution(series)

            profiles[col] = profile
        return profiles

    # ────────────────────────────────────────────
    # Fallback defaults (used before LLM runs)
    # ────────────────────────────────────────────
    @staticmethod
    def _default_imputation(semantic_type: str) -> str:
        """Rule-based fallback imputation before LLM runs."""
        defaults = {
            "Numeric":       "fill_median",
            "Categorical":   "fill_mode",
            "Name":          "fill_none",
            "Email":         "fill_none",
            "Phone":         "fill_none",
            "Location":      "fill_none",
            "ID_Code":       "fill_none",
            "Structured_ID": "fill_none",
            "Temporal":      "fill_none",
            "Financial":     "fill_none",
            "Currency":      "fill_none",
            "Geospatial":    "leave_empty",
            "Free_Text":     "leave_empty",
            "Binary_Flag":   "fill_mode",
            "Score_Rating":  "fill_median",
            "Percentage":    "fill_median",
            "URL":           "leave_empty",
            "JSON_Field":    "leave_empty",
        }
        return defaults.get(semantic_type, "leave_empty")
