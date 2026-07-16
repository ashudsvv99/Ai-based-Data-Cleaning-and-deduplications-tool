"""
Post-cleaning validator: checks that cleaning was performed correctly,
computes confidence scores, and flags suspicious transformations.

All validation rules are derived dynamically from the SchemaAgent's
semantic_type classification. No column names are hardcoded.
This means the validator works correctly on ANY dataset, not just
e-commerce or healthcare datasets.
"""
import re
import pandas as pd
from typing import Dict
from backend.schema_detector import has_non_ascii, column_non_ascii_ratio

# RFC-compliant email regex (permissive but catches the obvious failures)
_EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

# Phone: 7-15 digits (international range), optional leading +
_PHONE_REGEX = re.compile(r'^\+?\d{7,15}$')

# Known placeholder / dummy email values
_DUMMY_EMAIL_PATTERNS = re.compile(
    r'^(nomail|noemail|test@test|none|n/a|na|null|invalid|fake|dummy|no_email)(@|$)',
    re.IGNORECASE
)


class Validator:
    """
    Validates the cleaned dataset against expected outcomes.

    Schema-driven: all checks are based on the semantic_type assigned
    by the SchemaAgent. No column names are hardcoded.
    Works on any dataset: e-commerce, healthcare, HR, banking, etc.
    """

    def validate(self, df: pd.DataFrame, schema: dict) -> dict:
        """
        Run all validation checks and return a report.

        Args:
            df:     The cleaned DataFrame
            schema: Dict of {column: ColumnSchema} from SchemaAgent

        Returns:
            A validation report dict
        """
        issues = []
        column_scores = {}
        flagged_values = {}   # col -> list of problem strings

        for col, col_schema in schema.items():
            if col not in df.columns:
                continue

            sem_type = col_schema.semantic_type.lower()
            score = 100

            # -- Check 1: Non-ASCII remaining in categorical/name columns --
            if sem_type in ["categorical", "name"]:
                ratio = column_non_ascii_ratio(df[col])
                if ratio > 0:
                    penalty = min(50, ratio * 100)
                    score -= penalty
                    issues.append(
                        f"Column '{col}' ({col_schema.semantic_type}) still has {ratio:.1%} "
                        f"non-ASCII values after cleaning"
                    )

            # -- Check 2: Missing values remaining --
            missing_pct = df[col].isna().mean()
            if missing_pct > 0.5:
                score -= 20
                issues.append(
                    f"Column '{col}' has {missing_pct:.1%} missing values remaining"
                )

            # -- Check 3: Empty strings masquerading as valid --
            if pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                empty_count = (df[col].astype(str).str.strip() == "").sum()
                if empty_count > 0:
                    score -= 10
                    issues.append(f"Column '{col}' has {empty_count} empty string values")

            # -- Check 4: Schema-driven Email validation --
            if sem_type == "email":
                bad = self._validate_email_column(df[col], col)
                if bad:
                    score -= min(40, len(bad) * 5)
                    issues.extend(bad)
                    flagged_values[col] = bad

            # -- Check 5: Schema-driven Phone validation --
            if sem_type == "phone":
                bad = self._validate_phone_column(df[col], col)
                if bad:
                    score -= min(40, len(bad) * 5)
                    issues.extend(bad)
                    flagged_values[col] = bad

            # -- Check 6: Schema-driven Numeric range check --
            if sem_type == "numeric":
                bad = self._validate_numeric_column(df[col], col)
                if bad:
                    score -= min(30, len(bad) * 3)
                    issues.extend(bad)

            column_scores[col] = max(0, score)

        overall = sum(column_scores.values()) / max(len(column_scores), 1)

        # -- Check 7: Dynamic cross-column business rules --
        self._validate_business_rules(df, schema, issues)

        return {
            "overall_confidence": round(overall, 1),
            "column_scores": column_scores,
            "issues": issues,
            "total_issues": len(issues),
            "flagged_values": flagged_values,
        }

    # -----------------------------------------------------------------
    # Schema-driven format validators
    # -----------------------------------------------------------------

    def _validate_email_column(self, series: pd.Series, col_name: str) -> list:
        """
        Validates all non-null values in an Email-type column.
        Uses regex -- no hardcoded column names. Works for 'email',
        'contact_email', 'user_email', 'email_address', etc.
        Supports comma-separated consolidated emails.
        """
        problems = []
        for idx, val in series.dropna().items():
            s = str(val).strip()
            if not s:
                continue
            # Split comma-separated emails
            parts = [p.strip() for p in s.split(",") if p.strip()]
            if not parts:
                continue
            for email in parts:
                # Check for known dummy placeholders first
                if _DUMMY_EMAIL_PATTERNS.match(email):
                    problems.append(
                        f"Column '{col_name}' row {idx}: "
                        f"'{email}' is a placeholder/dummy email, not a real address"
                    )
                elif not _EMAIL_REGEX.match(email):
                    problems.append(
                        f"Column '{col_name}' row {idx}: "
                        f"'{email}' is not a valid email (missing @, TLD, or contains spaces)"
                    )
        return problems

    def _validate_phone_column(self, series: pd.Series, col_name: str) -> list:
        """
        Validates all non-null values in a Phone-type column.
        Checks digit count (7-15 international range) and non-numeric chars.
        Works for 'phone', 'mobile', 'contact_number', 'tel', etc.
        Supports comma-separated consolidated phones.
        """
        problems = []
        for idx, val in series.dropna().items():
            s = str(val).strip()
            if not s:
                continue
            # Split comma-separated phone numbers
            parts = [p.strip() for p in s.split(",") if p.strip()]
            if not parts:
                continue
            for phone in parts:
                digits_only = re.sub(r'[^\d]', '', phone)
                if not digits_only:
                    problems.append(
                        f"Column '{col_name}' row {idx}: "
                        f"'{phone}' does not contain any digits"
                    )
                    continue
                # All-same digit pattern (e.g. 0000000000, 9999999999)
                if len(set(digits_only)) == 1:
                    problems.append(
                        f"Column '{col_name}' row {idx}: "
                        f"'{phone}' looks like a placeholder (all same digit)"
                    )
                elif not re.match(r'^\+?\d+$', phone):
                    problems.append(
                        f"Column '{col_name}' row {idx}: "
                        f"'{phone}' contains non-numeric characters"
                    )
                elif not (7 <= len(digits_only) <= 15):
                    problems.append(
                        f"Column '{col_name}' row {idx}: "
                        f"'{phone}' has invalid length ({len(digits_only)} digits, expected 7-15)"
                    )
        return problems

    def _validate_numeric_column(self, series: pd.Series, col_name: str) -> list:
        """
        Checks for impossible negative values in any numeric column
        whose name suggests it should always be positive.
        This is flexible: columns like 'temperature' or 'profit' are skipped
        because negatives are valid there.
        """
        problems = []
        POSITIVE_ONLY_HINTS = [
            "price", "amount", "cost", "fee", "qty", "quantity", "count",
            "total", "revenue", "salary", "age", "weight", "height", "gst",
            "tax", "shipping", "discount"
        ]
        col_lower = col_name.lower()
        if not any(hint in col_lower for hint in POSITIVE_ONLY_HINTS):
            return problems  # Column might legitimately have negatives

        numeric = pd.to_numeric(series, errors='coerce')
        negative_count = (numeric < 0).sum()
        if negative_count > 0:
            problems.append(
                f"Business Rule: Column '{col_name}' has {negative_count} "
                f"negative values (expected non-negative for this field type)"
            )
        return problems

    # -----------------------------------------------------------------
    # Dynamic cross-column business rules
    # -----------------------------------------------------------------

    def _validate_business_rules(self, df: pd.DataFrame, schema: dict, issues: list):
        """
        Validates cross-column logic rules.
        Dynamically finds column pairs by semantic_type and keyword hints
        in column names -- no hardcoded column names anywhere.
        Works on any domain dataset.
        """
        col_map  = {c.lower(): c for c in df.columns}
        type_map = {c: s.semantic_type.lower() for c, s in schema.items() if c in df.columns}

        # Find all Temporal columns for date paradox check
        temporal_cols = [c for c, t in type_map.items() if t == "temporal"]

        # -- Rule 1: Delivery after Order (generalised for any date-pair) --
        # Dynamically matches 'order_date', 'purchase_date', 'created_at', etc.
        # against 'delivery_date', 'shipped_date', 'completed_at', etc.
        ORDER_HINTS    = ["order", "purchase", "start", "created", "placed", "open"]
        DELIVERY_HINTS = ["delivery", "delivered", "end", "close", "completed", "shipped", "resolved"]

        order_col    = None
        delivery_col = None
        for col in temporal_cols:
            cl = col.lower()
            if any(h in cl for h in ORDER_HINTS) and order_col is None:
                order_col = col
            if any(h in cl for h in DELIVERY_HINTS) and delivery_col is None:
                delivery_col = col

        if order_col and delivery_col:
            try:
                bad = (
                    pd.to_datetime(df[delivery_col], errors='coerce') <
                    pd.to_datetime(df[order_col], errors='coerce')
                ).sum()
                if bad > 0:
                    issues.append(
                        f"Business Rule Violation: {bad} rows have '{delivery_col}' "
                        f"before '{order_col}' (temporal paradox)"
                    )
            except Exception:
                pass

        # -- Rule 2: Discount column <= 100% --
        discount_col = next(
            (col_map[c] for c in col_map if "discount" in c and "amount" not in c), None
        )
        if discount_col:
            bad = (pd.to_numeric(df[discount_col], errors='coerce') > 100).sum()
            if bad > 0:
                issues.append(
                    f"Business Rule Violation: {bad} rows have a discount > 100% "
                    f"in column '{discount_col}'"
                )

        # -- Rule 3: Sentinel placeholder values (-100, -999, -9999) --
        for col, stype in type_map.items():
            if stype == "numeric":
                numeric = pd.to_numeric(df[col], errors='coerce')
                sentinel_count = numeric.isin([-100, -999, -1, -9999]).sum()
                if sentinel_count > 0:
                    issues.append(
                        f"Data Quality: Column '{col}' has {sentinel_count} rows with "
                        f"likely sentinel/placeholder values (-100, -999, etc.)"
                    )
