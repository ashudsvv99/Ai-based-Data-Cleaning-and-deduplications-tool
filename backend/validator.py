"""
Post-cleaning validator: checks that cleaning was performed correctly,
computes confidence scores, and flags suspicious transformations.
"""
import pandas as pd
from typing import Dict
from backend.schema_detector import has_non_ascii, column_non_ascii_ratio


class Validator:
    """
    Validates the cleaned dataset against expected outcomes:
    - All categorical columns should contain only English values
    - Name columns should contain only ASCII characters
    - No empty strings masquerading as valid values
    """

    def validate(self, df: pd.DataFrame, schema: dict) -> dict:
        """
        Run all validation checks and return a report.

        Args:
            df: The cleaned DataFrame
            schema: Dict of {column: ColumnSchema} from SchemaAgent

        Returns:
            A validation report dict
        """
        issues = []
        column_scores = {}

        for col, col_schema in schema.items():
            if col not in df.columns:
                continue

            sem_type = col_schema.semantic_type
            score = 100  # Start at 100, deduct for issues

            # Check 1: Non-ASCII remaining in categorical/name columns
            if sem_type in ["Categorical", "Name"]:
                ratio = column_non_ascii_ratio(df[col])
                if ratio > 0:
                    penalty = min(50, ratio * 100)
                    score -= penalty
                    issues.append(
                        f"Column '{col}' ({sem_type}) still has {ratio:.1%} non-ASCII values after cleaning"
                    )

            # Check 2: Missing values remaining
            missing_pct = df[col].isna().mean()
            if missing_pct > 0.5:
                score -= 20
                issues.append(
                    f"Column '{col}' has {missing_pct:.1%} missing values"
                )

            # Check 3: Empty string masquerading as valid
            if pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                empty_count = (df[col].astype(str).str.strip() == "").sum()
                if empty_count > 0:
                    score -= 10
                    issues.append(
                        f"Column '{col}' has {empty_count} empty string values"
                    )

            column_scores[col] = max(0, score)

        overall = sum(column_scores.values()) / max(len(column_scores), 1)

        # Check 4: Hard Business Rule Validation (Domain specific rules)
        self._validate_business_rules(df, issues)

        return {
            "overall_confidence": round(overall, 1),
            "column_scores": column_scores,
            "issues": issues,
            "total_issues": len(issues),
        }

    def _validate_business_rules(self, df: pd.DataFrame, issues: list):
        """Validates specific domain and mathematical business rules."""
        col_map = {c.lower(): c for c in df.columns}

        # Rule 1: Delivery date after order date
        if "order_date" in col_map and "delivery_date" in col_map:
            try:
                invalid_dates = (pd.to_datetime(df[col_map["delivery_date"]]) < pd.to_datetime(df[col_map["order_date"]])).sum()
                if invalid_dates > 0:
                    issues.append(f"Business Rule Violation: {invalid_dates} rows have a delivery date before the order date.")
            except Exception:
                pass
                
        # Rule 2: Discount <= 100%
        discount_col = next((c for c in col_map.keys() if "discount" in c and "amount" not in c), None)
        if discount_col:
            invalid_discounts = (pd.to_numeric(df[col_map[discount_col]], errors='coerce') > 100).sum()
            if invalid_discounts > 0:
                issues.append(f"Business Rule Violation: {invalid_discounts} rows have a discount greater than 100%.")

        # Rule 3: Quantity > 0
        if "quantity" in col_map:
            invalid_qty = (pd.to_numeric(df[col_map["quantity"]], errors='coerce') <= 0).sum()
            if invalid_qty > 0:
                issues.append(f"Business Rule Violation: {invalid_qty} rows have a quantity ≤ 0.")

        # Rule 4: GST >= 0
        if "gst" in col_map:
            invalid_gst = (pd.to_numeric(df[col_map["gst"]], errors='coerce') < 0).sum()
            if invalid_gst > 0:
                issues.append(f"Business Rule Violation: {invalid_gst} rows have a negative GST.")

