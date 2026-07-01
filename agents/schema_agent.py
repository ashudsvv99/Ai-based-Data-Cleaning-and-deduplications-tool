"""
LLM-assisted schema agent.

Three-pass column classification:
1. Heuristic pass  — fast, reliable, no LLM. Classifies semantic type.
2. LLM pass        — only for columns with heuristic confidence < 0.80.
3. LLM imputation  — LLM inspects each column's actual distribution
                     (missing %, skew, unique ratio) and picks the best
                     imputation method with reasoning.
"""
import json
import pandas as pd
import numpy as np
from typing import Dict
from pydantic import BaseModel, Field
from agents.llm_client import LMStudioClient
from backend.schema_detector import classify_all_columns


class ColumnSchema(BaseModel):
    semantic_type: str = Field(
        description="One of: Name, Email, Phone, Location, ID_Code, Numeric, Temporal, Categorical, Free_Text"
    )
    imputation_strategy: str = Field(default="leave_empty")
    imputation_reasoning: str = Field(default="")
    needs_multilingual: bool = Field(default=False)
    non_ascii_ratio: float = Field(default=0.0)
    description: str = Field(default="Heuristic classification")


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
    def classify_columns(self, df: pd.DataFrame, log_callback=print) -> Dict[str, ColumnSchema]:
        """Full three-pass classification."""

        # ── Pass 1: Heuristic ──
        log_callback("SchemaAgent: Pass 1 — Heuristic classification...")
        heuristic_results = classify_all_columns(df)

        schema: Dict[str, ColumnSchema] = {}
        ambiguous_cols = []

        for col, info in heuristic_results.items():
            sem_type   = info["semantic_type"]
            confidence = info["confidence"]
            needs_ml   = info["needs_multilingual"]

            schema[col] = ColumnSchema(
                semantic_type=sem_type,
                imputation_strategy=self._default_imputation(sem_type),
                needs_multilingual=needs_ml,
                non_ascii_ratio=info["non_ascii_ratio"],
                description=f"Heuristic ({confidence:.0%} confidence)",
            )
            if confidence < 0.80:
                ambiguous_cols.append(col)

        # ── Pass 2: LLM for ambiguous columns ──
        if ambiguous_cols:
            log_callback(f"SchemaAgent: Pass 2 — LLM refinement for {len(ambiguous_cols)} ambiguous columns...")
            llm_schema = self._llm_classify(df, ambiguous_cols)
            for col, llm_info in llm_schema.items():
                if col in schema and isinstance(llm_info, dict):
                    schema[col].semantic_type = llm_info.get("semantic_type", schema[col].semantic_type)
                    schema[col].description   = "LLM classification"
            # Re-check multilingual after override
            for col in ambiguous_cols:
                if col in schema:
                    schema[col].needs_multilingual = heuristic_results.get(col, {}).get("non_ascii_ratio", 0) > 0.01

        # ── Pass 3: LLM-chosen imputation ──
        log_callback("SchemaAgent: Pass 3 — LLM imputation strategy selection...")
        self._llm_choose_imputation(df, schema)

        # Print summary
        for col, s in schema.items():
            ml_flag = " [MULTILINGUAL]" if s.needs_multilingual else ""
            log_callback(f"  -> {col}: {s.semantic_type} | impute={s.imputation_strategy}{ml_flag}")
            if s.imputation_reasoning:
                log_callback(f"       Reason: {s.imputation_reasoning}")

        return schema

    # ────────────────────────────────────────────
    # Pass 2: LLM semantic type classifier
    # ────────────────────────────────────────────
    def _llm_classify(self, df: pd.DataFrame, columns: list) -> dict:
        sample_data = df[columns].head(5).to_dict(orient="records")
        system_prompt = (
            "You are an expert Data Engineer. Classify each column into ONE semantic type:\n"
            "Name, Email, Phone, Location, ID_Code, Numeric, Temporal, Categorical, Free_Text\n\n"
            "Return ONLY a JSON object where each key is a column name and the value is:\n"
            '{"semantic_type": "<type>"}\n\n'
            "EXAMPLE OUTPUT:\n"
            '{"full_name": {"semantic_type": "Name"}, "order_status": {"semantic_type": "Categorical"}}'
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
        self, df: pd.DataFrame, schema: Dict[str, ColumnSchema]
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
        system_prompt = (
            "You are an expert Data Scientist specializing in missing value imputation.\n"
            "For each column described below, choose the BEST imputation strategy.\n\n"
            "Available strategies:\n"
            "  fill_mean   — use for normally distributed numeric columns\n"
            "  fill_median — use for skewed numeric columns or when outliers exist\n"
            "  fill_mode   — use for categorical, low-cardinality, or heavily repeated values\n"
            "  leave_empty — use for IDs, names, free text, or when imputation is harmful\n\n"
            "Return ONLY a JSON object where each key is the column name and value is:\n"
            '{"strategy": "<strategy>", "reasoning": "<one sentence>"}\n\n'
            "EXAMPLE:\n"
            '{"age": {"strategy": "fill_median", "reasoning": "Age is slightly right-skewed; median is more robust than mean."},\n'
            ' "customer_type": {"strategy": "fill_mode", "reasoning": "Low-cardinality categorical; mode fills the most common segment."}}'
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

        valid_strategies = {"fill_mean", "fill_median", "fill_mode", "leave_empty"}
        for col, info in result.items():
            if col in schema and isinstance(info, dict):
                strategy  = str(info.get("strategy", "")).strip().lower()
                reasoning = str(info.get("reasoning", "")).strip()
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
            "Numeric":    "fill_median",
            "Categorical":"fill_mode",
            "Name":       "leave_empty",
            "Email":      "leave_empty",
            "Phone":      "leave_empty",
            "Location":   "fill_mode",
            "ID_Code":    "leave_empty",
            "Temporal":   "leave_empty",
            "Free_Text":  "leave_empty",
        }
        return defaults.get(semantic_type, "leave_empty")
