import pandas as pd
from typing import Dict, List, Tuple
from agents.schema_agent import ColumnSchema

class QualityFilter:
    """
    Evaluates row-level data quality and aggressively drops rows that lack
    business value (e.g., completely empty, highly sparse, or missing critical identifiers).
    """

    def __init__(self, df: pd.DataFrame, schema_mapping: Dict[str, ColumnSchema]):
        self.df = df
        self.schema = schema_mapping
        self.stats = {
            "initial_rows": len(df),
            "dropped_columns": 0,
            "dropped_empty": 0,
            "dropped_sparse": 0,
            "dropped_missing_critical": 0,
            "dropped_dummy": 0
        }

    def _get_columns_by_semantic_type(self, semantic_type: str) -> List[str]:
        return [col for col, schema in self.schema.items() if semantic_type in schema.semantic_type.lower()]

    def filter_useless_rows(self) -> pd.DataFrame:
        """
        Drop rows that are completely useless according to universal business rules.
        """
        df_clean = self.df.copy()

        # 0. Column-Level Check: Drop completely empty or highly sparse columns (>90% missing)
        initial_cols = len(df_clean.columns)
        col_thresh = int(len(df_clean) * 0.1) # Must have at least 10% non-NA values
        df_clean = df_clean.dropna(axis=1, thresh=col_thresh)
        self.stats["dropped_columns"] = initial_cols - len(df_clean.columns)

        # 1. Row-Level Check: Drop completely empty rows (or rows where ALL columns are NaN/None/empty)
        initial_len = len(df_clean)
        df_clean = df_clean.dropna(how='all')
        self.stats["dropped_empty"] = initial_len - len(df_clean)

        # 2. Row-Level Check: Drop highly sparse rows (>50% missing data)
        threshold = len(df_clean.columns) // 2
        initial_len = len(df_clean)
        df_clean = df_clean.dropna(thresh=threshold)
        self.stats["dropped_sparse"] = initial_len - len(df_clean)

        # 3. Critical Identifier Check
        # Identify critical columns (contact info, identity, location) by name or schema
        critical_keywords = ["email", "phone", "mobile", "contact", "city", "address", "location", "name", "customer"]
        critical_cols = []
        for col in df_clean.columns:
            col_lower = str(col).lower()
            schema_type = self.schema[col].semantic_type.lower() if col in self.schema else ""
            if any(k in col_lower or k in schema_type for k in critical_keywords):
                critical_cols.append(col)

        if len(critical_cols) > 1:
            min_required = len(critical_cols) - 1
            initial_len = len(df_clean)
            df_clean = df_clean.dropna(subset=critical_cols, thresh=min_required)
            self.stats["dropped_missing_critical"] = initial_len - len(df_clean)

        # 4. Explicit Test/Dummy Data Filter
        # Drop rows that are explicitly marked as "test" or "unknown" across critical text fields.
        # Check string columns for dummy phrases.
        str_cols = df_clean.select_dtypes(include=['object', 'string']).columns
        if not str_cols.empty:
            # Pattern looking for obvious dummy rows: "test user", "test@test", "unknown customer"
            dummy_pattern = r'^(test\s*user|test@|unknown\s*customer|dummy\s*data)$'
            
            # We flag a row as dummy if any of its string columns match the exact dummy pattern
            mask = pd.Series(False, index=df_clean.index)
            for col in str_cols:
                mask |= df_clean[col].astype(str).str.strip().str.lower().str.match(dummy_pattern, na=False)
            
            initial_len = len(df_clean)
            df_clean = df_clean[~mask]
            self.stats["dropped_dummy"] = initial_len - len(df_clean)

        return df_clean

    def get_report(self) -> str:
        total_dropped_rows = (self.stats["dropped_empty"] + 
                         self.stats["dropped_sparse"] + 
                         self.stats["dropped_missing_critical"] +
                         self.stats["dropped_dummy"])
        total_dropped_cols = self.stats["dropped_columns"]

        if total_dropped_rows == 0 and total_dropped_cols == 0:
            return "No rows or columns were dropped for quality issues."
        
        report = ""
        if total_dropped_cols > 0:
            report += f"Dropped {total_dropped_cols} sparse columns (>90% missing). "
        
        if total_dropped_rows > 0:
            report += f"Dropped {total_dropped_rows} unrecoverable rows: "
            reasons = []
            if self.stats["dropped_empty"]: reasons.append(f"{self.stats['dropped_empty']} completely empty")
            if self.stats["dropped_sparse"]: reasons.append(f"{self.stats['dropped_sparse']} highly sparse (>50% missing)")
            if self.stats["dropped_missing_critical"]: reasons.append(f"{self.stats['dropped_missing_critical']} missing multiple critical business fields (e.g. Email, Phone, City)")
            if self.stats["dropped_dummy"]: reasons.append(f"{self.stats['dropped_dummy']} explicit dummy/test data")
            report += ", ".join(reasons) + "."
        
        return report.strip()
