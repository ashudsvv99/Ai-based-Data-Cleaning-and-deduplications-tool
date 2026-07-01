"""
Planner agent: maps semantic column types to deterministic cleaning strategies,
and generates LLM-guided smart imputation rules based on column relationships.
"""
import json
import os
from typing import Dict, List
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
    Also generates LLM-guided smart imputation rules.
    """

    def __init__(self, llm_client: LMStudioClient = None):
        self.llm_client = llm_client or LMStudioClient()

    def plan(self, schema_mapping: Dict[str, ColumnSchema], log_callback=print) -> Dict[str, CleaningStrategy]:
        """Map each column's semantic type to a cleaning strategy."""
        log_callback("PlannerAgent: Formulating cleaning strategy...")

        strategies = {}
        for col_name, schema in schema_mapping.items():
            strategy = self._map_strategy(schema)
            strategies[col_name] = strategy

        return strategies

    def generate_smart_imputation_rules(
        self,
        df: pd.DataFrame,
        schema_mapping: Dict[str, ColumnSchema],
        log_callback=print
    ) -> List[ImputationRule]:
        """
        Ask the LLM to generate context-aware imputation rules
        based on column relationships.
        """
        # Build context for the LLM
        columns_info = []
        for col, schema in schema_mapping.items():
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                unique_vals = df[col].dropna().unique()[:10]
                columns_info.append({
                    "column": col,
                    "type": schema.semantic_type,
                    "missing_count": int(missing_count),
                    "sample_values": [str(v) for v in unique_vals],
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

        user_prompt = (
            f"Dataset columns with missing values:\n"
            f"{json.dumps(columns_info, ensure_ascii=False, default=str)}\n\n"
            f"Generate smart imputation rules."
        )

        log_callback("PlannerAgent: Querying LLM for smart imputation rules...")
        result = self.llm_client.chat_completion_json(
            system_prompt, user_prompt, num_expected_keys=len(columns_info) * 2, enable_thinking=True
        )

        rules = []
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and "target_column" in item:
                    try:
                        rule = ImputationRule(**item)
                        rules.append(rule)
                        log_callback(f"  -> IF {rule.condition} THEN {rule.target_column} = '{rule.fill_value}' (confidence: {rule.confidence}%)")
                    except Exception as e:
                        log_callback(f"PlannerAgent: Failed to parse rule {item}: {e}")
            log_callback(f"PlannerAgent: Generated {len(rules)} smart imputation rules.")

        return rules

    def _map_strategy(self, schema: ColumnSchema) -> CleaningStrategy:
        """Map a semantic type to specific cleaning algorithms."""
        sem = schema.semantic_type.lower()
        imputation = schema.imputation_strategy or "leave_empty"
        needs_ml = schema.needs_multilingual

        if any(loc in sem for loc in ["location", "city", "state", "country", "address", "pincode"]):
            return CleaningStrategy(
                imputation=imputation,
                normalization="translate_to_english" if needs_ml else "title_case",
                deduplication="blocking_key",
                needs_multilingual=needs_ml,
            )
        elif "name" in sem:
            return CleaningStrategy(
                imputation=imputation,
                normalization="transliterate_name" if needs_ml else "title_case",
                deduplication="fuzzy_name",
                needs_multilingual=needs_ml,
            )
        elif "email" in sem:
            return CleaningStrategy(
                imputation=imputation,
                normalization="normalize_email",
                deduplication="exact_match",
            )
        elif "phone" in sem:
            return CleaningStrategy(
                imputation=imputation,
                normalization="normalize_phone",
                deduplication="exact_match",
            )
        elif "id_code" in sem:
            return CleaningStrategy(
                imputation=imputation,
                normalization="uppercase_strip",
                deduplication="none",
            )
        elif "categorical" in sem:
            return CleaningStrategy(
                imputation=imputation,
                normalization="translate_to_english" if needs_ml else "standardize_case",
                deduplication="none",
                needs_multilingual=needs_ml,
            )
        elif "numeric" in sem:
            return CleaningStrategy(
                imputation=imputation,
                normalization="coerce_numeric",
                deduplication="none",
            )
        elif "temporal" in sem:
            return CleaningStrategy(
                imputation=imputation,
                normalization="parse_dates",
                deduplication="none",
            )
        else:
            return CleaningStrategy(
                imputation=imputation,
                normalization="none",
                deduplication="none",
            )
