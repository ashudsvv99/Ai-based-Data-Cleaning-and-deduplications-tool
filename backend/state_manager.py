import os
import json
import pickle
import pandas as pd

class StateManager:
    """
    Manages persistent state across Streamlit hard refreshes (F5) by saving
    critical data to a local hidden .cache directory.
    """
    
    CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")
    PIPELINE_CACHE_FILE = os.path.join(CACHE_DIR, "pipeline_state.pkl")
    DB_CREDS_CACHE_FILE = os.path.join(CACHE_DIR, "db_credentials.json")

    @classmethod
    def _ensure_dir(cls):
        if not os.path.exists(cls.CACHE_DIR):
            os.makedirs(cls.CACHE_DIR, exist_ok=True)

    @classmethod
    def save_pipeline_state(cls, cleaned_df: pd.DataFrame, metadata: dict, table_name: str, logs: list):
        cls._ensure_dir()
        try:
            with open(cls.PIPELINE_CACHE_FILE, "wb") as f:
                pickle.dump({"df": cleaned_df, "meta": metadata, "table": table_name, "logs": logs}, f)
        except Exception as e:
            print(f"Failed to save pipeline state: {e}")

    @classmethod
    def load_pipeline_state(cls):
        if os.path.exists(cls.PIPELINE_CACHE_FILE):
            try:
                with open(cls.PIPELINE_CACHE_FILE, "rb") as f:
                    data = pickle.load(f)
                    return data.get("df"), data.get("meta"), data.get("table"), data.get("logs", [])
            except Exception as e:
                print(f"Failed to load pipeline state: {e}")
        return None, None, None, []

    @classmethod
    def clear_pipeline_state(cls):
        if os.path.exists(cls.PIPELINE_CACHE_FILE):
            try:
                os.remove(cls.PIPELINE_CACHE_FILE)
            except Exception:
                pass

    @classmethod
    def save_db_credentials(cls, params: dict):
        cls._ensure_dir()
        try:
            with open(cls.DB_CREDS_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(params, f, indent=4)
        except Exception as e:
            print(f"Failed to save DB credentials: {e}")

    @classmethod
    def load_db_credentials(cls) -> dict:
        if os.path.exists(cls.DB_CREDS_CACHE_FILE):
            try:
                with open(cls.DB_CREDS_CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load DB credentials: {e}")
        return {}
