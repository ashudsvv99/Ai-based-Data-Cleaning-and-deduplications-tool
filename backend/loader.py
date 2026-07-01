"""
Universal dataset loader with encoding detection, file size validation,
and memory optimization.
"""
import os
import pandas as pd
import config


class UniversalLoader:
    """
    Loads CSV / Excel files with safety checks and memory optimization.
    Unlike the old loader, this does NOT convert strings to category dtype
    because that causes issues in downstream cleaning modules.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.extension = os.path.splitext(filepath)[1].lower()

    def load_and_optimize(self) -> pd.DataFrame:
        """Load a dataset, validate it, clean missing markers, and optimize memory."""
        self._validate_file()

        print(f"Loading dataset: {self.filepath}...")

        if self.extension == ".csv":
            try:
                df = pd.read_csv(self.filepath, engine="pyarrow")
            except Exception:
                # Fallback for encoding issues
                df = pd.read_csv(self.filepath, encoding="utf-8-sig")
        elif self.extension in [".xls", ".xlsx"]:
            df = pd.read_excel(self.filepath, engine="openpyxl")
        else:
            raise ValueError(f"Unsupported file format: {self.extension}")

        # Replace known missing-value markers with pd.NA
        df = df.replace(config.MISSING_VALUE_MARKERS, pd.NA)
        df = df.replace(r'^\s*$', pd.NA, regex=True)

        # Strip column names
        df.columns = [str(c).strip() for c in df.columns]

        print(f"  Memory before optimization: {df.memory_usage(deep=True).sum() / (1024*1024):.2f} MB")
        df = self._optimize_memory(df)
        print(f"  Memory after optimization:  {df.memory_usage(deep=True).sum() / (1024*1024):.2f} MB")

        return df

    def _validate_file(self):
        """Check file exists, extension is supported, and size is within limits."""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")

        if self.extension not in config.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{self.extension}'. "
                f"Supported: {config.SUPPORTED_EXTENSIONS}"
            )

        size_mb = os.path.getsize(self.filepath) / (1024 * 1024)
        if size_mb > config.MAX_FILE_SIZE_MB:
            raise ValueError(
                f"File is {size_mb:.1f} MB, which exceeds the "
                f"{config.MAX_FILE_SIZE_MB} MB limit."
            )

    @staticmethod
    def _optimize_memory(df: pd.DataFrame) -> pd.DataFrame:
        """Downcast numeric types to save memory. Strings stay as object dtype."""
        for col in df.select_dtypes(include=["float64"]).columns:
            df[col] = pd.to_numeric(df[col], downcast="float")

        for col in df.select_dtypes(include=["int64"]).columns:
            df[col] = pd.to_numeric(df[col], downcast="integer")

        return df
