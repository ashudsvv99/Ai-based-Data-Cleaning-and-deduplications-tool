"""
Planner agent: maps semantic column types to deterministic cleaning strategies,
and generates LLM-guided smart imputation rules based on column relationships.

v4 — New semantic types added:
  - Geospatial    → leave_empty, no dedup (lat/lon coordinates)
  - Currency      → fill_none, no dedup (monetary values with symbols)
  - Structured_ID → fill_none, uppercase_strip, no dedup (PAN/Aadhaar/GSTIN/etc.)

v3 — fill_none for business-sensitive columns:
  - Business-sensitive columns (Email, Phone, ID_Code, Name, Location, Financial)
    use fill_none: standardizes sentinel strings → real None/NaN, never fabricates.
  - Non-business columns (Numeric, Categorical, Score, Percentage) get statistical imputation.
  - LLM smart rules are blocked for business-sensitive column names.

v2 — Email/Phone deduplication = "none":
  - Family-guard logic in DeduplicationEngine handles them internally.
  - Passing "exact_match" caused false merges on shared family emails/phones.
"""
import json
import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from agents.llm_client import LMStudioClient
from agents.schema_agent import ColumnSchema
import pandas as pd


class CleaningStrategy(BaseModel):
    imputation: str = Field(description="How to handle missing values")
    normalization: str = Field(description="How to normalize the text")
    deduplication: str = Field(description="How to handle deduplication")
    needs_multilingual: bool = Field(default=False)


class ImputationRule(BaseModel):
    target_column: str
    condition: str          # e.g. "customer_type == 'B2B'" or "always"
    fill_value: str
    confidence: int = 50


class PlannerAgent:
    """
    Creates a deterministic execution plan from the semantic schema.
    Also generates LLM-guided smart imputation rules with domain awareness.
    """

    def __init__(self, llm_client: LMStudioClient = None):
        self.llm_client = llm_client or LMStudioClient()

    def plan(
        self,
        schema_mapping: Dict[str, ColumnSchema],
        log_callback=print,
        domain: str = "Generic",
        dataset_intent: str = "Non-Predictive Business",
    ) -> Dict[str, CleaningStrategy]:
        """Map each column's semantic type to a cleaning strategy."""
        log_callback(f"PlannerAgent: Formulating cleaning strategy (domain={domain}, intent={dataset_intent})...")

        strategies = {}
        for col_name, schema in schema_mapping.items():
            strategy = self._map_strategy(schema, domain=domain, dataset_intent=dataset_intent)
            strategies[col_name] = strategy

        return strategies

    def generate_smart_imputation_rules(
        self,
        df: pd.DataFrame,
        schema_mapping: Dict[str, ColumnSchema],
        log_callback=print,
        domain: str = "Generic",
        dataset_intent: str = "Non-Predictive Business",
    ) -> List[ImputationRule]:
        """
        Ask the LLM to generate context-aware imputation rules
        based on column relationships and domain knowledge.
        """
        # Build context for the LLM
        columns_info = []
        for col, schema in schema_mapping.items():
            missing_count = df[col].isna().sum() if col in df.columns else 0
            if missing_count > 0:
                unique_vals = df[col].dropna().unique()[:10] if col in df.columns else []
                columns_info.append({
                    "column":        col,
                    "type":          schema.semantic_type,
                    "missing_count": int(missing_count),
                    "sample_values": [str(v) for v in unique_vals],
                    "is_critical":   schema.is_critical_business,
                    "is_target":     schema.is_target,
                })

        if not columns_info:
            log_callback("PlannerAgent: No missing values detected. Skipping smart imputation rules.")
            return []

        # Load prompt template
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "planner.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = (
                "Generate context-aware imputation rules as a JSON array. "
                "Each rule: {target_column, condition, fill_value, confidence}. "
                "Return ONLY JSON."
            )

        # Inject domain and intent context into the prompt
        domain_context = (
            f"\n\nDataset Domain: {domain}\n"
            f"Dataset Intent: {dataset_intent}\n"
            f"Apply domain-specific knowledge when choosing fill values.\n"
        )

        user_prompt = (
            f"Dataset columns with missing values:\n"
            f"{json.dumps(columns_info, ensure_ascii=False, default=str)}\n"
            f"{domain_context}\n"
            f"Generate smart imputation rules."
        )

        log_callback("PlannerAgent: Querying LLM for smart imputation rules...")
        result = self.llm_client.chat_completion_json(
            system_prompt, user_prompt,
            num_expected_keys=len(columns_info) * 2,
            enable_thinking=True,
        )

        rules = []
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and "target_column" in item:
                    try:
                        rule = ImputationRule(**item)
                        # Safety: never generate rules for critical business/target columns
                        col_schema = schema_mapping.get(rule.target_column)
                        if col_schema and (col_schema.is_critical_business or col_schema.is_target):
                            log_callback(f"  [Planner] Skipped rule for critical/target column: '{rule.target_column}'")
                            continue
                        rules.append(rule)
                        log_callback(
                            f"  -> IF {rule.condition} THEN {rule.target_column} = "
                            f"'{rule.fill_value}' (confidence: {rule.confidence}%)"
                        )
                    except Exception as e:
                        log_callback(f"PlannerAgent: Failed to parse rule {item}: {e}")
            log_callback(f"PlannerAgent: Generated {len(rules)} smart imputation rules.")

        return rules

    def _map_strategy(
        self,
        schema: ColumnSchema,
        domain: str = "Generic",
        dataset_intent: str = "Non-Predictive Business",
    ) -> CleaningStrategy:
        """Map a semantic type to specific cleaning algorithms."""
        sem = schema.semantic_type.lower()
        imputation = schema.imputation_strategy or "leave_empty"
        needs_ml = schema.needs_multilingual

        # ── Location / Address ────────────────────────────────────
        if any(loc in sem for loc in ["location", "city", "state", "country", "address", "pincode"]):
            return CleaningStrategy(
                imputation=imputation,
                normalization="translate_to_english" if needs_ml else "title_case",
                deduplication="blocking_key",
                needs_multilingual=needs_ml,
            )

        # ── Name ─────────────────────────────────────────────────
        elif "name" in sem:
            return CleaningStrategy(
                imputation="fill_none",
                normalization="transliterate_name" if needs_ml else "title_case",
                deduplication="fuzzy_name",
                needs_multilingual=needs_ml,
            )

        # ── Email ─────────────────────────────────────────────────
        # CRITICAL FIX: deduplication = "none"
        # Email can be shared by family members. The DeduplicationEngine's
        # family-guard rules handle it internally. Passing "exact_match" here
        # caused the engine to incorrectly merge different-named people who
        # share a family email address.
        # imputation = fill_none: never fabricate email; normalize sentinels → None/NaN
        elif "email" in sem:
            return CleaningStrategy(
                imputation="fill_none",
                normalization="normalize_email",
                deduplication="none",
            )

        # ── Phone ─────────────────────────────────────────────────
        # Same reason as email — shared by family, guard handled in engine.
        # imputation = fill_none: never fabricate phone; normalize sentinels → None/NaN
        elif "phone" in sem:
            return CleaningStrategy(
                imputation="fill_none",
                normalization="normalize_phone",
                deduplication="none",
            )

        # ── ID / Code ───────────────────────────────────────────────
        elif "id_code" in sem:
            return CleaningStrategy(
                imputation="fill_none",   # ← business-sensitive ID: no fabrication
                normalization="uppercase_strip",
                deduplication="none",
            )

        # ── Financial (salary, payment methods, banking) ───────────────
        # Never statistically impute financial/compensation data.
        elif "financial" in sem:
            return CleaningStrategy(
                imputation="fill_none",   # ← NEVER statistically impute financial data
                normalization="none",
                deduplication="none",
            )

        # ── Binary Flag (0/1, True/False, Yes/No) ─────────────────
        elif "binary_flag" in sem:
            return CleaningStrategy(
                imputation=imputation if imputation != "leave_empty" else "fill_mode",
                normalization="coerce_numeric",
                deduplication="none",
            )

        # ── Score / Rating ────────────────────────────────────────
        elif "score_rating" in sem or "score" in sem or "rating" in sem:
            return CleaningStrategy(
                imputation=imputation if imputation != "leave_empty" else "fill_median",
                normalization="coerce_numeric",
                deduplication="none",
            )

        # ── Percentage ────────────────────────────────────────────
        elif "percentage" in sem or "percent" in sem:
            return CleaningStrategy(
                imputation=imputation if imputation != "leave_empty" else "fill_median",
                normalization="coerce_numeric",
                deduplication="none",
            )

        # ── URL ───────────────────────────────────────────────────
        elif "url" in sem or "link" in sem or "website" in sem:
            return CleaningStrategy(
                imputation="leave_empty",
                normalization="none",
                deduplication="none",
            )

        # ── Geospatial (lat/lon) ───────────────────────────────────
        elif "geospatial" in sem:
            return CleaningStrategy(
                imputation="leave_empty",   # Cannot impute coordinates
                normalization="coerce_numeric",
                deduplication="none",
            )

        # ── Currency (monetary values with symbols) ────────────────
        elif "currency" in sem:
            return CleaningStrategy(
                imputation="fill_none",     # Don't fabricate monetary values
                normalization="coerce_numeric",
                deduplication="none",
            )

        # ── Structured_ID (PAN, Aadhaar, GSTIN, SSN, IFSC) ────────
        elif "structured_id" in sem:
            return CleaningStrategy(
                imputation="fill_none",     # Never fabricate structured IDs
                normalization="uppercase_strip",
                deduplication="none",
            )

        # ── Categorical ───────────────────────────────────────────
        elif "categorical" in sem:
            return CleaningStrategy(
                imputation=imputation,
                normalization="translate_to_english" if needs_ml else "standardize_case",
                deduplication="none",
                needs_multilingual=needs_ml,
            )

        # ── Numeric ───────────────────────────────────────────────
        elif "numeric" in sem:
            # Domain-aware default for numeric imputation
            domain_numeric_default = self._domain_numeric_default(domain, dataset_intent)
            final_impute = imputation if imputation not in ("leave_empty",) else domain_numeric_default
            return CleaningStrategy(
                imputation=final_impute,
                normalization="coerce_numeric",
                deduplication="none",
            )

        # ── Temporal / Date ───────────────────────────────────────
        elif "temporal" in sem:
            return CleaningStrategy(
                imputation=imputation,
                normalization="parse_dates",
                deduplication="none",
            )

        # ── Free Text / JSON ──────────────────────────────────────
        else:
            return CleaningStrategy(
                imputation="leave_empty",
                normalization="none",
                deduplication="none",
            )

    @staticmethod
    def _domain_numeric_default(domain: str, intent: str) -> str:
        """
        Choose a sensible default numeric imputation based on domain.
        - Predictive datasets: fill_median (keeps distribution for ML)
        - Finance: fill_median (amounts are skewed)
        - Healthcare: fill_median (vitals/age are skewed)
        - HR: fill_median (salary is skewed)
        - Others: fill_median as safe default
        """
        if intent == "Predictive":
            return "fill_median"
        domain_lower = domain.lower()
        if any(d in domain_lower for d in ["finance", "healthcare", "hr", "insurance", "pharma"]):
            return "fill_median"
        if any(d in domain_lower for d in ["retail", "ecom", "e-commerce", "logistics"]):
            return "fill_median"
        return "fill_median"  # Safe universal default
