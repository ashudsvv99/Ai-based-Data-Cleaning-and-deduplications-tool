"""
Universal dataset loader with encoding detection, file size validation,
and memory optimization.
"""
import os
import pandas as pd
import config


class UniversalLoader:
    """
    Universal dataset loader capable of loading from CSV/Excel files,
    live database tables, or wrapping an existing DataFrame.
    """

    def __init__(self, filepath: str = None, df: pd.DataFrame = None):
        """Internal constructor. Use from_file(), from_dataframe(), or from_database()."""
        self.filepath = filepath
        self.df = df
        if self.filepath:
            self.extension = os.path.splitext(self.filepath)[1].lower()
        else:
            self.extension = None

    @classmethod
    def from_file(cls, filepath: str) -> "UniversalLoader":
        """Load from CSV or Excel file."""
        return cls(filepath=filepath)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "UniversalLoader":
        """Wrap an already-loaded DataFrame."""
        return cls(df=df)

    @classmethod
    def from_database(cls, connector, table_name: str, limit: int = 100_000) -> "UniversalLoader":
        """Load a DB table via DatabaseConnector.load_table()."""
        df = connector.load_table(table_name, limit=limit)
        return cls(df=df)

    def load_and_optimize(self) -> pd.DataFrame:
        """Load a dataset, validate it, clean missing markers, and optimize memory."""
        if self.filepath:
            self._validate_file()
            print(f"Loading dataset: {self.filepath}...")

            if self.extension == ".csv":
                try:
                    df = pd.read_csv(self.filepath, engine="pyarrow")
                except Exception:
                    df = pd.read_csv(self.filepath, encoding="utf-8-sig")
            elif self.extension in [".xls", ".xlsx"]:
                df = pd.read_excel(self.filepath, engine="openpyxl")
            else:
                raise ValueError(f"Unsupported file format: {self.extension}")
        elif self.df is not None:
            print("Loading dataset from DataFrame...")
            # We copy to avoid modifying original
            df = self.df.copy()
        else:
            raise ValueError("Neither filepath nor DataFrame was provided.")

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
