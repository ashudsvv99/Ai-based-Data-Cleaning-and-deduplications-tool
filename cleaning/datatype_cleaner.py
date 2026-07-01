"""
Data type cleaner: detects and fixes mixed-type columns,
coerces strings to numbers, and handles boolean variations.
"""
import pandas as pd
import numpy as np


class DataTypeCleaner:
    """Fix mixed-type columns and coerce values to their correct types."""

    @staticmethod
    def fix_numeric_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
        """Attempt to coerce specified columns to numeric, setting errors to NaN."""
        for col in columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    @staticmethod
    def fix_boolean_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
        """Standardize boolean variations (yes/no, true/false, 1/0) to True/False."""
        true_vals = {"yes", "y", "true", "1", "t", "on"}
        false_vals = {"no", "n", "false", "0", "f", "off"}

        for col in columns:
            if col in df.columns:
                def coerce_bool(val):
                    if pd.isna(val):
                        return pd.NA
                    s = str(val).strip().lower()
                    if s in true_vals:
                        return True
                    if s in false_vals:
                        return False
                    return val
                df[col] = df[col].apply(coerce_bool)
        return df

    @staticmethod
    def detect_mixed_types(df: pd.DataFrame) -> dict:
        """Identify columns that contain a mix of numeric and string values."""
        mixed = {}
        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]):
                non_null = df[col].dropna()
                if len(non_null) == 0:
                    continue
                numeric_count = pd.to_numeric(non_null, errors="coerce").notna().sum()
                string_count = len(non_null) - numeric_count
                if numeric_count > 0 and string_count > 0:
                    mixed[col] = {
                        "numeric_count": int(numeric_count),
                        "string_count": int(string_count),
                    }
        return mixed
