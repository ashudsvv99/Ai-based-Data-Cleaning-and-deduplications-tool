"""
Pure-heuristic schema detector that classifies columns WITHOUT any LLM calls.
This acts as the primary classifier; the LLM SchemaAgent is only consulted
for columns where the heuristic confidenc            e is low.
"""
import re
import unicodedata
import pandas as pd
from typing import Dict, Tuple
import config


# Unicode script ranges for detecting non-Latin content
SCRIPT_RANGES = {
    "Devanagari": (0x0900, 0x097F),
    "Bengali":    (0x0980, 0x09FF),
    "Gurmukhi":   (0x0A00, 0x0A7F),
    "Gujarati":   (0x0A80, 0x0AFF),
    "Tamil":      (0x0B80, 0x0BFF),
    "Telugu":     (0x0C00, 0x0C7F),
    "Kannada":    (0x0C80, 0x0CFF),
    "Malayalam":  (0x0D00, 0x0D7F),
    "Cyrillic":   (0x0400, 0x04FF),
    "Arabic":     (0x0600, 0x06FF),
    "CJK":        (0x4E00, 0x9FFF),
    "Hangul":     (0xAC00, 0xD7AF),
}


def detect_script(text: str) -> str:
    """Detect the dominant non-Latin script in a string."""
    if not text or not isinstance(text, str):
        return "Latin"
    for char in text:
        cp = ord(char)
        for script_name, (low, high) in SCRIPT_RANGES.items():
            if low <= cp <= high:
                return script_name
    return "Latin"


def has_non_ascii(text: str) -> bool:
    """Check if a string contains any non-ASCII characters."""
    if not text or not isinstance(text, str):
        return False
    try:
        text.encode("ascii")
        return False
    except UnicodeEncodeError:
        return True


def column_non_ascii_ratio(series: pd.Series) -> float:
    """Return the fraction of non-null values that contain non-ASCII characters."""
    valid = series.dropna().astype(str)
    if len(valid) == 0:
        return 0.0
    non_ascii_count = sum(1 for v in valid if has_non_ascii(str(v).strip()))
    return non_ascii_count / len(valid)


def column_script_distribution(series: pd.Series) -> Dict[str, int]:
    """Return a count of values per detected script in a column."""
    dist = {}
    for val in series.dropna().astype(str):
        script = detect_script(str(val).strip())
        dist[script] = dist.get(script, 0) + 1
    return dist


# ──────────────────────────────────────────────
# Column name keyword patterns
# ──────────────────────────────────────────────
NAME_KEYWORDS = ["name", "full_name", "first_name", "last_name", "customer_name",
                 "employee_name", "patient_name", "person", "contact_name"]
EMAIL_KEYWORDS = ["email", "e_mail", "mail", "email_address"]
PHONE_KEYWORDS = ["phone", "mobile", "telephone", "cell", "contact_number", "tel"]
LOCATION_KEYWORDS = ["city", "country", "state", "address", "zip", "postal",
                     "location", "region", "district", "area", "pincode"]
ID_KEYWORDS = ["id", "code", "sku", "mrn", "account_number", "record_id",
               "customer_id", "patient_id", "employee_id", "order_id", "invoice"]
TEMPORAL_KEYWORDS = ["date", "time", "timestamp", "created_at", "updated_at",
                     "dob", "birth", "expiry", "deadline"]


def classify_column(col_name: str, series: pd.Series) -> Tuple[str, float, bool]:
    """
    Classify a single column using heuristics.

    Returns:
        (semantic_type, confidence, needs_multilingual_processing)
    """
    col_lower = col_name.lower().replace(" ", "_").replace("-", "_")
    dtype = series.dtype
    num_unique = series.nunique()
    total = len(series.dropna())
    non_ascii = column_non_ascii_ratio(series)

    # ── Priority 1: Column name keywords ──
    if any(kw in col_lower for kw in EMAIL_KEYWORDS):
        return "Email", 0.95, False

    if any(kw in col_lower for kw in PHONE_KEYWORDS):
        return "Phone", 0.95, False

    if any(kw in col_lower for kw in NAME_KEYWORDS):
        return "Name", 0.95, non_ascii > config.MIN_NON_ASCII_RATIO

    if any(kw in col_lower for kw in LOCATION_KEYWORDS):
        return "Location", 0.90, non_ascii > config.MIN_NON_ASCII_RATIO

    if any(kw in col_lower for kw in ID_KEYWORDS):
        return "ID_Code", 0.90, False

    if any(kw in col_lower for kw in TEMPORAL_KEYWORDS):
        return "Temporal", 0.90, False

    # ── Priority 2: Dtype-based detection ──
    if pd.api.types.is_numeric_dtype(dtype):
        return "Numeric", 0.85, False

    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "Temporal", 0.85, False

    # ── Priority 3: Content-based detection ──
    if pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
        unique_ratio = num_unique / max(total, 1)

        # Low cardinality string = Categorical
        if num_unique < config.CATEGORICAL_MAX_UNIQUE or unique_ratio < config.CATEGORICAL_UNIQUE_RATIO:
            return "Categorical", 0.80, non_ascii > config.MIN_NON_ASCII_RATIO

        # High cardinality string - could be Name or Free_Text
        # Check if values look like multi-word proper nouns (names)
        sample = series.dropna().head(20).astype(str)
        word_counts = sample.str.split().str.len()
        avg_words = word_counts.mean() if len(word_counts) > 0 else 0

        if 1.5 <= avg_words <= 4:
            # Looks like names (2-3 words typical)
            return "Name", 0.60, non_ascii > config.MIN_NON_ASCII_RATIO

        return "Free_Text", 0.50, non_ascii > config.MIN_NON_ASCII_RATIO

    return "Free_Text", 0.40, non_ascii > config.MIN_NON_ASCII_RATIO


def classify_all_columns(df: pd.DataFrame) -> Dict[str, dict]:
    """
    Classify every column in a DataFrame using heuristics.

    Returns:
        {
            "column_name": {
                "semantic_type": "Name",
                "confidence": 0.95,
                "needs_multilingual": True,
                "non_ascii_ratio": 0.45,
                "scripts_detected": {"Devanagari": 30, "Bengali": 15, "Latin": 55}
            }
        }
    """
    result = {}
    for col in df.columns:
        sem_type, confidence, needs_ml = classify_column(col, df[col])

        scripts = {}
        non_ascii = 0.0
        if pd.api.types.is_string_dtype(df[col].dtype) or pd.api.types.is_object_dtype(df[col].dtype):
            non_ascii = column_non_ascii_ratio(df[col])
            if non_ascii > 0:
                scripts = column_script_distribution(df[col])

        result[col] = {
            "semantic_type": sem_type,
            "confidence": confidence,
            "needs_multilingual": needs_ml,
            "non_ascii_ratio": round(non_ascii, 4),
            "scripts_detected": scripts,
        }

    return result
