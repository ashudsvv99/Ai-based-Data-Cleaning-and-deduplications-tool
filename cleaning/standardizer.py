"""
Standardizer: applies translation/transliteration mappings to DataFrame columns,
and handles simple normalizations (casing, whitespace, email, phone).
"""
import re
import pandas as pd
from typing import Dict
from cleaning.multilingual import MultilingualEngine


class Standardizer:
    """
    Applies cleaning transformations to DataFrame columns.
    Uses the MultilingualEngine for translation/transliteration,
    and regex/string ops for simple normalizations.
    """

    def __init__(self, multilingual_engine: MultilingualEngine = None):
        self.ml_engine = multilingual_engine
        self.stats = {}

    def apply(self, df: pd.DataFrame, column: str, strategy: str) -> pd.DataFrame:
        """
        Apply a normalization strategy to a column.
        """
        if strategy == "none":
            return df

        # Convert column to string safely, preserving NA
        safe_col = df[column].apply(
            lambda x: str(x).strip() if pd.notna(x) else ""
        ).replace(
            ["nan", "None", "<NA>", "<Na>", "pd.NA", "NoneType"], ""
        )

        if strategy == "transliterate_name":
            df = self._apply_name_transliteration(df, column, safe_col)

        elif strategy == "translate_to_english":
            df = self._apply_categorical_translation(df, column, safe_col)

        elif strategy == "standardize_case":
            df[column] = self._standardize_casing(safe_col)

        elif strategy == "title_case":
            df[column] = safe_col.apply(
                lambda x: x.title() if x else pd.NA
            )

        elif strategy == "uppercase_strip":
            df[column] = safe_col.apply(
                lambda x: x.upper().strip() if x else pd.NA
            )

        elif strategy == "normalize_email":
            df[column] = safe_col.apply(self._clean_email)

        elif strategy == "normalize_phone":
            df[column] = safe_col.apply(self._clean_phone)

        elif strategy == "coerce_numeric":
            df = self._coerce_numeric(df, column)

        elif strategy == "parse_dates":
            df = self._parse_dates(df, column)

        return df

    def _apply_name_transliteration(
        self, df: pd.DataFrame, column: str, safe_col: pd.Series
    ) -> pd.DataFrame:
        """Transliterate names using the multilingual engine."""
        if not self.ml_engine:
            df[column] = safe_col.apply(lambda x: x.title() if x else pd.NA)
            return df

        mapping = self.ml_engine.transliterate_name_column(df[column])
        self.stats[column] = {
            "task": "Name Transliteration",
            "items_processed": len(mapping),
            "mapping": mapping,
        }

        def apply_map(x):
            if not x or x in ["", "nan", "None"]:
                return pd.NA
            result = mapping.get(x, x)
            return re.sub(r'\s+', ' ', str(result)).title() if result else pd.NA

        df[column] = safe_col.apply(apply_map)
        return df

    def _apply_categorical_translation(
        self, df: pd.DataFrame, column: str, safe_col: pd.Series
    ) -> pd.DataFrame:
        """Translate and standardize categorical values using the multilingual engine."""
        if not self.ml_engine:
            df[column] = self._standardize_casing(safe_col)
            return df

        mapping = self.ml_engine.translate_categorical_column(df[column], column)
        self.stats[column] = {
            "task": "Translation/Standardization",
            "items_processed": len(mapping),
            "mapping": mapping,
        }

        def apply_map(x):
            if not x or x in ["", "nan", "None"]:
                return pd.NA
            result = mapping.get(x, x)
            result_str = str(result).strip()
            if result_str.lower() in ["nan", "none", "", "null"]:
                return pd.NA
            # Preserve known acronyms
            if result_str.upper() in ["B2B", "B2C", "B2G", "COD"]:
                return result_str.upper()
            return result_str.title()

        df[column] = safe_col.apply(apply_map)
        return df

    @staticmethod
    def _standardize_casing(series: pd.Series) -> pd.Series:
        """Normalize casing and fix minor categorical typos using frequency-based fuzzy matching."""
        def norm(x):
            if pd.isna(x) or not x:
                return pd.NA
            x = str(x).strip()
            if x.upper() in ["B2B", "B2C", "B2G", "COD"]:
                return x.upper()
            return x.title()
            
        normalized = series.apply(norm)
        
        # Spelling correction for low-cardinality categoricals
        counts = normalized.value_counts()
        if len(counts) == 0 or len(counts) > 100:
            return normalized
            
        # Heuristic: Categories appearing multiple times are 'canonical', those appearing once are potential typos
        canonical_categories = counts[counts >= 3].index.tolist()
        potential_typos = counts[counts < 3].index.tolist()
        
        if not canonical_categories or not potential_typos:
            return normalized
            
        from rapidfuzz import process, fuzz
        
        correction_map = {}
        for typo in potential_typos:
            match = process.extractOne(typo, canonical_categories, scorer=fuzz.token_sort_ratio)
            if match and match[1] >= 85:  # 85% similarity threshold for typo correction
                correction_map[typo] = match[0]
                
        if correction_map:
            return normalized.replace(correction_map)
            
        return normalized

    @staticmethod
    def _clean_email(val: str) -> object:
        if not val:
            return pd.NA
        val = str(val).lower().strip()
        val = re.sub(r'(\.at\.|\ [at\ ]|\s+at\s+)', '@', val)
        val = re.sub(r'\s+', '', val)
        # Strict extraction: find first valid email-like structure
        match = re.search(r'[a-z0-9\.\_\%\+\-]+@[a-z0-9\.\-]+\.[a-z]{2,}', val)
        return match.group(0) if match else pd.NA

    @staticmethod
    def _clean_phone(val: str) -> object:
        if not val:
            return pd.NA
        digits = re.sub(r'\D', '', str(val))
        if len(digits) > 10:
            if digits.startswith('91') and len(digits) == 12:
                digits = digits[2:]
            elif digits.startswith('1') and len(digits) == 11:
                digits = digits[1:]
        # Strict bound: ITU says max 15 digits, min ~7
        return digits if 7 <= len(digits) <= 15 else pd.NA

    @staticmethod
    def _coerce_numeric(df: pd.DataFrame, column: str) -> pd.DataFrame:
        df[column] = pd.to_numeric(df[column], errors="coerce")
        return df

    @staticmethod
    def _parse_dates(df: pd.DataFrame, column: str) -> pd.DataFrame:
        try:
            # Aggressive datetime inference using pandas dateutil hooks
            parsed = pd.to_datetime(df[column], errors="coerce")
            # Convert successfully parsed dates to standard ISO 8601 string format
            df[column] = parsed.dt.strftime('%Y-%m-%d')
            # Any failures become pd.NA naturally via coerce
            df[column] = df[column].astype(object).where(df[column].notna(), pd.NA)
        except Exception:
            pass
        return df
