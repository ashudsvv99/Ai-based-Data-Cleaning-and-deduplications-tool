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
        # Drop rows whose IDENTIFIER columns (Email, Name, ID) contain known
        # test/placeholder values. Uses the schema to find which columns to
        # check -- no column names hardcoded.
        #
        # The pattern is broad enough to cover real-world sentinel values
        # like 'nomail', 'test@test.com', 'unknown customer', 'N/A', etc.
        IDENTIFIER_TYPES = {"email", "name", "id_code", "phone"}
        identifier_cols = [
            col for col, sch in self.schema.items()
            if sch.semantic_type.lower() in IDENTIFIER_TYPES and col in df_clean.columns
        ]
        # Fall back to all string columns if schema has no identifiers
        if not identifier_cols:
            identifier_cols = list(df_clean.select_dtypes(include=['object', 'string']).columns)

        dummy_pattern = (
            r'^('
            r'test\s*user|test@|unknown\s*customer|dummy\s*data|'
            r'nomail|noemail|no\s*mail|no\s*email|'
            r'n/a|na|none|null|unknown|'
            r'0{7,}|9{7,}|'       # e.g. 0000000000 or 9999999999
            r'xxx+|aaa+|zzz+|'   # repeated filler chars
            r'-999|-9999|-1'      # sentinel numerics in string fields
            r')$'
        )

        # A row is dummy only if ALL its identifier columns match dummy pattern
        # (avoids false drops where just one optional field is blank)
        if identifier_cols:
            dummy_mask = pd.Series(True, index=df_clean.index)
            for col in identifier_cols:
                col_matches = df_clean[col].astype(str).str.strip().str.lower().str.match(
                    dummy_pattern, na=False
                )
                dummy_mask &= col_matches | df_clean[col].isna()

            # Only drop if MORE than one identifier is a dummy value
            # (one missing field is normal; all missing = clearly fake row)
            dummy_score = pd.DataFrame({
                col: df_clean[col].astype(str).str.strip().str.lower().str.match(
                    dummy_pattern, na=False
                )
                for col in identifier_cols
            }).sum(axis=1)
            row_is_dummy = dummy_score >= max(2, len(identifier_cols) // 2)
        else:
            row_is_dummy = pd.Series(False, index=df_clean.index)

        initial_len = len(df_clean)
        df_clean = df_clean[~row_is_dummy]
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
