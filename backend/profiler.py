"""
Dataset profiler: computes quality metrics, detects scripts, and
identifies data quality issues before the cleaning pipeline runs.
"""
import pandas as pd
from backend.schema_detector import column_non_ascii_ratio, column_script_distribution


class DatasetProfiler:
    """
    Generates a comprehensive quality profile of a dataset including
    missing values, duplicates, script distribution, and a quality score.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def profile(self) -> dict:
        total_rows = len(self.df)
        total_cols = len(self.df.columns)

        missing_counts = self.df.isnull().sum()
        missing_pct = (missing_counts / total_rows) * 100

        exact_duplicates = self.df.duplicated().sum()

        column_stats = {}
        for col in self.df.columns:
            stats = {
                "dtype": str(self.df[col].dtype),
                "null_count": int(missing_counts[col]),
                "null_percentage": round(float(missing_pct[col]), 2),
                "unique_values": int(self.df[col].nunique()),
            }

            # Script analysis for string columns
            if pd.api.types.is_string_dtype(self.df[col]) or pd.api.types.is_object_dtype(self.df[col]):
                stats["non_ascii_ratio"] = round(column_non_ascii_ratio(self.df[col]), 4)
                if stats["non_ascii_ratio"] > 0:
                    stats["scripts"] = column_script_distribution(self.df[col])

            column_stats[col] = stats

        # Quality score: 0-100 (higher is better)
        total_cells = total_rows * total_cols
        total_missing = int(missing_counts.sum())
        missing_penalty = (total_missing / max(total_cells, 1)) * 40
        duplicate_penalty = (exact_duplicates / max(total_rows, 1)) * 30
        quality_score = max(0, round(100 - missing_penalty - duplicate_penalty, 1))

        return {
            "total_rows": total_rows,
            "total_columns": total_cols,
            "exact_duplicate_rows": int(exact_duplicates),
            "total_missing_cells": total_missing,
            "memory_usage_mb": round(
                self.df.memory_usage(deep=True).sum() / (1024 * 1024), 2
            ),
            "quality_score": quality_score,
            "column_statistics": column_stats,
        }
