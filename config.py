"""
Central configuration for AI_Data_Cleaner.
All tunable parameters are defined here so they can be adjusted
without modifying any module code.
"""
import os
import psutil

# ──────────────────────────────────────────────
# LLM Settings (LM Studio / local model)
# ──────────────────────────────────────────────
LLM_BASE_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
LLM_MODEL_NAME = "local-model"
LLM_TEMPERATURE = 0.1          # Low temperature for deterministic JSON outputs
LLM_MAX_TOKENS_DEFAULT = 4096  # Default max tokens per response 
LLM_MAX_TOKENS_CEILING = 16384 # Upper limit for dynamic token calculation 
LLM_TIMEOUT_SECONDS = 600      # 10 minutes 
LLM_MAX_RETRIES = 3            # Number of retries on failure
LLM_RETRY_DELAY_SECONDS = 5    # Base delay between retries (doubles each time)

# Chunking: max items to send per LLM call
# Modern local LLMs can safely process larger chunks.
# On a 32GB system, you can safely increase this to 50 or 100.
LLM_CHUNK_SIZE = 25


# ──────────────────────────────────────────────
# Data Loading
# ──────────────────────────────────────────────
# Dynamically allocate max file size based on system RAM configuration.
# Rule of thumb: allow 100MB of file size per 1GB of total system RAM, as 
# Pandas dataframes usually consume 5x to 10x the raw file size in memory.
try:
    total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    dynamic_max_size = int(total_ram_gb * 100)
    MAX_FILE_SIZE_MB = max(200, dynamic_max_size) # Default to at least 200MB, scales to ~3200MB on 32GB RAM
except Exception:
    MAX_FILE_SIZE_MB = 200 # Fallback
SUPPORTED_EXTENSIONS = [".csv", ".xlsx", ".xls"]
# Strings that should be treated as missing values during load
MISSING_VALUE_MARKERS = [
    "Unknown", "-", "unknown", "None", "nan", "NaN",
    "<Na>", "<NA>", "NA", "N/A", "n/a", "null", "NULL",
    "NoneType", "pd.NA", "",
]


# ──────────────────────────────────────────────
# Schema Detection
# ──────────────────────────────────────────────
# Columns with fewer unique values than this ratio are treated as categorical
CATEGORICAL_UNIQUE_RATIO = 0.05   # If unique/total < 5%, it's categorical
CATEGORICAL_MAX_UNIQUE = 50       # Or if unique count < 50


# ──────────────────────────────────────────────
# Cleaning Thresholds
# ──────────────────────────────────────────────
FUZZY_MATCH_THRESHOLD = 80         # Minimum fuzz ratio to consider two names the same
OUTLIER_IQR_MULTIPLIER = 1.5      # Standard IQR multiplier for outlier clipping
MIN_NON_ASCII_RATIO = 0.01        # If > 1% of column values are non-ASCII, flag for translation


# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_LEVEL = "INFO"


# ──────────────────────────────────────────────
# Directories
# ──────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(PROJECT_ROOT, "uploads")
EXPORTS_DIR = os.path.join(PROJECT_ROOT, "exports")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
