"""
Advanced outlier detection and handling using IQR, Z-Score, and domain-aware capping.
Supports detection logging, per-column method selection, and reports for the UI.
"""
import pandas as pd
import numpy as np
import config


class OutlierHandler:
    """
    Multi-strategy outlier detection and handling:
    - IQR (Interquartile Range): robust for skewed distributions
    - Z-Score: best for normally distributed data
    - Domain-aware boundary capping (e.g., age > 0, salary > 0)

    Intent-Aware Behaviour:
    - Non-Predictive Business datasets: statistical outlier clipping (IQR/Z-score)
      is SKIPPED for business metric columns (revenue, balance, purchase amounts,
      customer credit, etc.). These may be genuine high-value customer records.
      Physical boundary checks (age > 120, negative prices) still apply.
    - Predictive datasets: full outlier handling runs on all numeric columns.
    """

    # Hard domain-aware physical boundaries for common columns
    DOMAIN_BOUNDS = {
        "age":               (0, 120),
        "salary":            (0, 5_000_000),
        "price":             (0, None),
        "cost":              (0, None),
        "weight":            (0, None),
        "weight_kg":         (0, None),
        "score":             (0, 100),
        "credit_score":      (300, 900),
        "performance_rating":(0, 5),
        "rating":            (0, 5),
        "quantity":          (0, None),
        "discount":          (0, 100),
        "percentage":        (0, 100),
        "height":            (0, 300),
        "bmi":               (10, 70),
    }

    # Business metric columns that must NOT be IQR/Z-score clipped
    # in Non-Predictive Business mode — high values may be genuine.
    BUSINESS_METRIC_PATTERNS = [
        "revenue", "income", "balance", "amount", "turnover", "profit",
        "sales", "purchase", "payment", "transaction", "value",
        "credit", "debit", "loan", "asset", "liability", "net_worth",
        "spend", "budget", "total", "sum", "billing",
    ]

    def __init__(self, multiplier: float = None, zscore_threshold: float = 3.0,
                 dataset_intent: str = ""):
        self.multiplier       = multiplier or config.OUTLIER_IQR_MULTIPLIER
        self.zscore_threshold = zscore_threshold
        self.dataset_intent   = dataset_intent
        # {column: {"method": str, "outliers_found": int, "lower": float, "upper": float, "action": str}}
        self.stats = {}

    # ─────────────────────────────────────────────────────────────
    # Per-column strategy selector
    # ─────────────────────────────────────────────────────────────
    def _choose_method(self, series: pd.Series, col_name: str) -> str:
        """
        Automatically choose IQR vs Z-Score based on distribution skewness
        and whether hard domain bounds exist for the column.
        """
        col_lower = col_name.lower()
        # If a hard boundary exists for this column, always use domain-capping first
        for key in self.DOMAIN_BOUNDS:
            if key in col_lower:
                return "domain_cap"

        non_null = series.dropna()
        if len(non_null) < 4:
            return "iqr"  # Not enough data for z-score

        skewness = abs(float(non_null.skew()))
        # If data is highly skewed, IQR is more robust
        return "iqr" if skewness > 1.0 else "zscore"

    # ─────────────────────────────────────────────────────────────
    # IQR Clipping
    # ─────────────────────────────────────────────────────────────
    def clip_iqr(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Clip outliers using the IQR method."""
        if not pd.api.types.is_numeric_dtype(df[column]):
            return df

        non_null = df[column].dropna()
        if len(non_null) < 4:
            return df

        Q1    = non_null.quantile(0.25)
        Q3    = non_null.quantile(0.75)
        IQR   = Q3 - Q1
        lower = Q1 - self.multiplier * IQR
        upper = Q3 + self.multiplier * IQR

        outlier_mask = (df[column] < lower) | (df[column] > upper)
        outliers     = int(outlier_mask.sum())

        self.stats[column] = {
            "method":        "IQR",
            "outliers_found": outliers,
            "lower":         round(lower, 4),
            "upper":         round(upper, 4),
            "action":        "clipped" if outliers > 0 else "none",
        }

        if outliers > 0:
            df[column] = df[column].clip(lower=lower, upper=upper)
            print(f"  [Outlier-IQR] '{column}': {outliers} outliers clipped to [{lower:.3g}, {upper:.3g}]")

        return df

    # ─────────────────────────────────────────────────────────────
    # Z-Score Clipping
    # ─────────────────────────────────────────────────────────────
    def clip_zscore(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Clip outliers using the Z-Score method."""
        if not pd.api.types.is_numeric_dtype(df[column]):
            return df

        non_null = df[column].dropna()
        if len(non_null) < 4:
            return df

        mean = float(non_null.mean())
        std  = float(non_null.std())
        if std == 0:
            return df

        lower = mean - self.zscore_threshold * std
        upper = mean + self.zscore_threshold * std

        outlier_mask = (df[column] < lower) | (df[column] > upper)
        outliers     = int(outlier_mask.sum())

        self.stats[column] = {
            "method":         "Z-Score",
            "outliers_found": outliers,
            "lower":          round(lower, 4),
            "upper":          round(upper, 4),
            "action":         "clipped" if outliers > 0 else "none",
        }

        if outliers > 0:
            df[column] = df[column].clip(lower=lower, upper=upper)
            print(f"  [Outlier-Z]   '{column}': {outliers} outliers clipped to [{lower:.3g}, {upper:.3g}]")

        return df

    # ─────────────────────────────────────────────────────────────
    # Domain-aware hard boundary capping
    # ─────────────────────────────────────────────────────────────
    def cap_domain_bounds(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """
        Apply hard physical boundaries based on domain knowledge.
        e.g., age cannot be negative or > 120.
        Then follow up with IQR on the remaining data.
        """
        if not pd.api.types.is_numeric_dtype(df[column]):
            return df

        col_lower = column.lower()
        bounds    = None
        for key, (lo, hi) in self.DOMAIN_BOUNDS.items():
            if key in col_lower:
                bounds = (lo, hi)
                break

        if bounds is None:
            return df

        lo, hi           = bounds
        before_count     = df[column].notna().sum()
        domain_outliers  = 0
        
        # Calculate robust median for replacements
        median_val = df[column].dropna().median()

        if lo is not None:
            mask = df[column] < lo
            domain_outliers += int(mask.sum())
            if mask.sum() > 0:
                # Replace physically impossible values with median instead of boundary edge
                df.loc[mask, column] = median_val
                
        if hi is not None:
            mask = df[column] > hi
            domain_outliers += int(mask.sum())
            if mask.sum() > 0:
                df.loc[mask, column] = median_val

        # After domain fixing, pass the rest to IQR
        df = self.clip_iqr(df, column)

        # Merge stats
        iqr_stat = self.stats.get(column, {})
        self.stats[column] = {
            **iqr_stat,
            "method":              f"Domain Cap [{lo},{hi}] + IQR",
            "domain_outliers_fixed": domain_outliers,
        }

        if domain_outliers > 0:
            print(f"  [Outlier-Dom] '{column}': {domain_outliers} values outside domain bounds [{lo}, {hi}]")

        return df

    # ─────────────────────────────────────────────────────────────
    # Master entry point
    # ─────────────────────────────────────────────────────────────
    def handle_all_numeric(self, df: pd.DataFrame, columns: list) -> pd.DataFrame:
        """
        Auto-select the best outlier handling method per column
        and apply it across all specified numeric columns.

        In Non-Predictive Business mode:
          - Business metric columns (revenue, balance, etc.) skip statistical
            clipping but still get physical boundary capping.
        """
        is_business = self.dataset_intent == "Non-Predictive Business"

        for col in columns:
            if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
                continue

            col_lower = col.lower()

            # Check if this is a business metric column
            is_business_metric = is_business and any(
                pat in col_lower for pat in self.BUSINESS_METRIC_PATTERNS
            )

            # Always apply physical domain boundary checks
            has_domain_bound = any(key in col_lower for key in self.DOMAIN_BOUNDS)

            if is_business_metric and not has_domain_bound:
                # Skip statistical clipping — high values may be genuine
                print(f"  [Outlier-Skip] '{col}': business metric column — statistical clipping skipped (Non-Predictive Business mode)")
                self.stats[col] = {"method": "Skipped", "action": "business_metric_preserved"}
                continue

            method = self._choose_method(df[col], col)
            if method == "domain_cap":
                df = self.cap_domain_bounds(df, col)
            elif method == "zscore":
                df = self.clip_zscore(df, col)
            else:
                df = self.clip_iqr(df, col)

        return df
