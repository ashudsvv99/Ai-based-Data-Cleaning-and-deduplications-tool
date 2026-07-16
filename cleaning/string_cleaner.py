"""
String cleaner: handles whitespace normalization, unicode cleanup,
and basic text sanitization.
"""
import re
import unicodedata
import pandas as pd


class StringCleaner:
    """Pre-processing pass that cleans whitespace, unicode issues, and encoding artifacts."""

    @staticmethod
    def clean_column(series: pd.Series) -> pd.Series:
        """Apply standard string cleaning to a Series."""
        def clean(val):
            if pd.isna(val):
                return pd.NA
            s = str(val)
            # Remove HTML tags
            s = re.sub(r'<[^>]+>', ' ', s)
            # Remove invisible/formatting unicode chars (zero-width spaces, BOM, direction overrides)
            s = re.sub(r'[\u200b-\u200f\ufeff\u202a-\u202e]', '', s)
            # Normalize unicode (NFC form)
            s = unicodedata.normalize("NFC", s)
            # Collapse multiple spaces and structural newlines
            s = re.sub(r'\s+', ' ', s)
            # Strip leading/trailing whitespace
            s = s.strip()
            # Check if empty after cleaning
            if s in ["", "nan", "None", "<NA>", "NoneType", "null"]:
                return pd.NA
            return s
        return series.apply(clean)

    @staticmethod
    def clean_all_string_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Apply string cleaning to all object/string columns in the DataFrame."""
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                df[col] = StringCleaner.clean_column(df[col])
        return df
