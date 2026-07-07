"""
NL Query Agent — Converts natural language queries into SQL,
evaluates safety, manages backups, and executes against a live database.

Workflow:
  1. User types natural language (e.g. "show me duplicate records",
     "delete all rows where email is null", "find customers with age > 80")
  2. LLM generates a SQL statement with explanation
  3. If the SQL is destructive (UPDATE/DELETE/INSERT/DROP/TRUNCATE):
       a. Detect the affected table(s)
       b. Create an automatic backup (table-copy + CSV)
       c. Show the user the SQL, backup info, and ask for confirmation
  4. Execute the SQL and return results / affected row count
  5. Full audit log of every query session

Common NL → SQL examples supported:
  - "check for duplicate records" → SELECT with GROUP BY + HAVING COUNT > 1
  - "find missing email addresses" → SELECT WHERE email IS NULL
  - "delete rows with no name" → DELETE WHERE name IS NULL (with backup)
  - "update phone format to international" → UPDATE (with backup)
  - "show top 10 customers by revenue" → SELECT ... ORDER BY ... LIMIT 10
  - "count records per city" → SELECT city, COUNT(*) GROUP BY city
"""
import re
import json
import datetime
from typing import Optional, Tuple, List, Dict

from agents.llm_client import LMStudioClient


# ─────────────────────────────────────────────────────────────
# Destructive SQL detector
# ─────────────────────────────────────────────────────────────
_DESTRUCTIVE = re.compile(
    r'\b(UPDATE|DELETE|INSERT\s+INTO|DROP|TRUNCATE|ALTER\s+TABLE|REPLACE\s+INTO|MERGE)\b',
    re.IGNORECASE | re.MULTILINE,
)

_TABLE_FROM = re.compile(
    r'(?:FROM|UPDATE|INTO|TABLE)\s+"?(\w+)"?',
    re.IGNORECASE,
)


def _detect_destructive(sql: str) -> bool:
    return bool(_DESTRUCTIVE.search(sql))


def _extract_table_names(sql: str) -> List[str]:
    """Extract table names referenced in a SQL query."""
    matches = _TABLE_FROM.findall(sql)
    return list({m.strip().strip('"') for m in matches if m})


# ─────────────────────────────────────────────────────────────
# Query intent classifier (fast, no LLM)
# ─────────────────────────────────────────────────────────────
_READ_INTENTS = [
    "show", "find", "list", "display", "get", "fetch", "search",
    "count", "how many", "top", "first", "last", "select", "report",
    "check", "detect", "look for", "identify", "which", "what",
    "duplicate", "duplicates", "missing", "null", "empty",
    "average", "sum", "group", "distinct", "unique",
]

_WRITE_INTENTS = [
    "delete", "remove", "drop", "update", "set", "change", "replace",
    "insert", "add", "create", "truncate", "alter", "merge",
    "clean", "fix", "correct", "modify", "rename", "wipe", "purge",
]


def _classify_intent(user_query: str) -> str:
    """
    Fast heuristic: 'read' or 'write'.
    The LLM will generate the actual SQL; this is used for UX hints only.
    """
    ql = user_query.lower()
    if any(w in ql for w in _WRITE_INTENTS):
        return "write"
    return "read"


# ─────────────────────────────────────────────────────────────
# NL Query Agent
# ─────────────────────────────────────────────────────────────
class NLQueryAgent:
    """
    Translates natural language queries into SQL using the local LLM,
    handles safety checks, backups, and execution.
    """

    def __init__(self, llm_client: LMStudioClient = None):
        self.llm_client = llm_client or LMStudioClient()
        self.query_history: List[dict] = []   # Audit log

    # ─────────────────────────────────────────────────────────────
    # Core: NL → SQL
    # ─────────────────────────────────────────────────────────────
    def generate_sql(
        self,
        user_query: str,
        table_schema: dict,
        db_type: str = "PostgreSQL",
        dialect_notes: str = "",
        sample_data: str = "",
        all_tables: List[str] = None,
    ) -> dict:
        """
        Convert natural language to SQL using the LLM.

        Parameters
        ----------
        user_query    : The user's natural language question
        table_schema  : Output of DatabaseConnector.get_table_info()
        db_type       : "PostgreSQL" | "MySQL" | "SQLite" | "SQL Server" | etc.
        dialect_notes : Optional extra dialect hints
        sample_data   : String representation of sample data rows
        all_tables    : List of all table names in the database for relationship context

        Returns
        -------
        {
          "sql":             "<generated SQL>",
          "explanation":     "<plain-english explanation>",
          "is_destructive":  bool,
          "affected_tables": [...],
          "intent_type":     "read" | "write",
          "safety_warning":  "<message if destructive>",
          "confidence":      "High" | "Medium" | "Low"
        }
        """
        table_name = table_schema.get("table", "unknown")
        columns    = table_schema.get("columns", [])
        row_count  = table_schema.get("row_count", "?")
        pk_cols    = table_schema.get("pk_columns", [])

        col_desc = "\n".join(
            f"  - {c['name']} ({c['type']}) {'[PK]' if c['name'] in pk_cols else ''}"
            for c in columns
        )

        system_prompt = (
            f"You are an expert {db_type} SQL engineer.\n"
            f"The user has a database table: '{table_name}' with {row_count} rows.\n\n"
            f"Table schema:\n{col_desc}\n\n"
        )
        
        if all_tables:
            system_prompt += f"Other tables in this database: {', '.join(all_tables)}\n\n"
            
        if sample_data:
            system_prompt += f"Sample Data from '{table_name}':\n{sample_data}\n\n"
            
        system_prompt += (
    f"Database dialect: {db_type}. {dialect_notes}\n\n"
    "Your task: Convert the user's data cleaning or natural language query into a syntactically correct, optimized, and safe SQL statement based ONLY on the provided schema.\n\n"
    "CRITICAL RULES:\n"
    "1. SCHEMA ADHERENCE: Only reference tables and columns explicitly defined in the schema above. Do not assume or hallucinate columns. Match column casing exactly as defined.\n"
    "2. DUPLICATE DETECTION/REMOVAL: Never use 'SELECT *' with GROUP BY. You MUST explicitly SELECT the exact columns you are grouping by along with COUNT(*) to prevent 'only_full_group_by' compilation errors.\n"
    "   - Example: SELECT col1, col2, COUNT(*) FROM t GROUP BY col1, col2 HAVING COUNT(*) > 1\n"
    "3. MISSING VALUES & NULLS: Use 'IS NULL' or 'IS NOT NULL' for null validation. Use TRIM(col) = '' or LENGTH(col) = 0 for empty strings if the dialect supports it.\n"
    "4. DESTRUCTIVE OPERATIONS (CLEANING): For UPDATE, DELETE, or DROP operations, you MUST include a highly targeted WHERE clause. Never modify an entire table without strict conditions.\n"
    "5. DATA STANDARDIZATION: For string cleaning (casing, spaces, trimming), use standard functions like TRIM(), LOWER(), or UPPER() based on the dialect rules.\n"
    "6. TIME-BASED CLEANING: Use proper, dialect-specific date/time parsing and formatting functions (e.g., STR_TO_DATE for MySQL, TO_DATE or CAST for PostgreSQL).\n"
    "7. QUOTING & IDENTIFIERS: Strictly enforce dialect quoting rules. Use double-quotes (\") for PostgreSQL/Oracle, backticks (`) for MySQL, and square brackets ([]) for SQL Server.\n"
    "8. OUTPUT FORMAT: Return ONLY a raw JSON object. Do NOT wrap the response in markdown code blocks (e.g., do not use ```json ... ```). No conversational prose or explanations outside the JSON structure.\n\n"
    "Return this exact JSON structure:\n"
    "{\n"
    '  "sql": "<the clean, single-line or newline-escaped SQL statement>",\n'
    '  "explanation": "<detailed description of the cleaning logic applied>",\n'
    '  "confidence": "High" | "Medium" | "Low",\n'
    '  "safety_note": "<MUST contain a detailed warning if the SQL updates, deletes, or alters data; otherwise an empty string>"\n'
    "}"
)

        user_prompt = f"Natural language query: {user_query}\n\nOUTPUT JSON:"

        raw = self.llm_client.chat_completion_json(
            system_prompt, user_prompt,
            num_expected_keys=4,
            enable_thinking=True,
        )

        if not isinstance(raw, dict) or "sql" not in raw:
            # Fallback — wrap plain text if LLM returned non-JSON
            sql = str(raw) if raw else f"SELECT * FROM \"{table_name}\" LIMIT 100"
            raw = {"sql": sql, "explanation": "LLM returned unexpected format.", "confidence": "Low", "safety_note": ""}

        sql            = str(raw.get("sql", "")).strip()
        
        # Auto-correct ONLY_FULL_GROUP_BY issues if the LLM hallucinates SELECT *
        if re.search(r'SELECT\s+\*\s+FROM', sql, re.IGNORECASE) and re.search(r'GROUP\s+BY', sql, re.IGNORECASE):
            group_match = re.search(r'GROUP\s+BY\s+(.+?)(?:\s+HAVING|\s+ORDER|\s+LIMIT|;|$)', sql, re.IGNORECASE)
            if group_match:
                group_cols = group_match.group(1).strip()
                sql = re.sub(r'SELECT\s+\*', f'SELECT {group_cols}, COUNT(*) as _count', sql, flags=re.IGNORECASE)

        explanation    = str(raw.get("explanation", "")).strip()
        confidence     = str(raw.get("confidence", "Medium")).strip()
        safety_note    = str(raw.get("safety_note", "")).strip()

        is_dest        = _detect_destructive(sql)
        affected       = _extract_table_names(sql) if is_dest else []
        intent         = _classify_intent(user_query)

        safety_warning = ""
        if is_dest:
            safety_warning = (
                f"⚠️ This query will MODIFY DATA ({', '.join(affected or [table_name])}).\n"
                "A backup will be created automatically before execution."
            )
            if safety_note:
                safety_warning += f"\nAdditional note: {safety_note}"

        result = {
            "sql":             sql,
            "explanation":     explanation,
            "is_destructive":  is_dest,
            "affected_tables": affected if affected else ([table_name] if is_dest else []),
            "intent_type":     intent,
            "safety_warning":  safety_warning,
            "confidence":      confidence,
        }

        self.query_history.append({
            "timestamp":    datetime.datetime.now().isoformat(),
            "user_query":   user_query,
            **result,
        })

        return result

    # ─────────────────────────────────────────────────────────────
    # Execute with backup protection
    # ─────────────────────────────────────────────────────────────
    def execute_with_backup(
        self,
        connector,          # DatabaseConnector instance
        sql: str,
        query_meta: dict,   # output of generate_sql()
        backup_dir: str = ".",
        user_query: str = "",
        table_schema: dict = None,
        _retry_count: int = 0
    ) -> dict:
        """
        Execute SQL safely:
        - If destructive: backup all affected tables first
        - Then execute
        - Return comprehensive result

        Returns:
        {
          "success":        bool,
          "result_df":      pd.DataFrame | None,
          "rows_affected":  int,
          "backups":        [ {"table": ..., "backup_table": ..., "csv_path": ...} ],
          "error":          str | None,
          "execution_time": float,
        }
        """
        import time
        start = time.time()
        backups = []

        is_dest = query_meta.get("is_destructive", _detect_destructive(sql))
        affected_tables = query_meta.get("affected_tables", _extract_table_names(sql))

        # ── Step 1: Create backups if destructive ──────────────────
        if is_dest and affected_tables:
            for tbl in affected_tables:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                # Table-copy backup
                ok_tbl, backup_tbl = connector.create_backup(tbl, ts)
                # CSV backup
                ok_csv, csv_path   = connector.create_backup_csv(tbl, backup_dir)
                backups.append({
                    "table":        tbl,
                    "backup_table": backup_tbl if ok_tbl else None,
                    "csv_path":     csv_path   if ok_csv else None,
                    "table_ok":     ok_tbl,
                    "csv_ok":       ok_csv,
                })

        # ── Step 2: Execute SQL ────────────────────────────────────
        result_df, error = connector.execute_query(sql)
        
        # ── Step 2b: Auto-Retry Logic on DB Error ──────────────────
        if error is not None and _retry_count < 1 and user_query and table_schema:
            print(f"[NLQueryAgent] Execution failed: {error}. Attempting auto-retry...")
            system_prompt = (
                f"You previously generated this SQL:\n{sql}\n\n"
                f"It failed with this database error:\n{error}\n\n"
                f"Please fix the SQL to resolve the error. Strictly use the provided schema:\n{table_schema}\n"
                f"Return ONLY the fixed SQL inside the JSON structure."
            )
            raw = self.llm_client.chat_completion_json(system_prompt, user_query, num_expected_keys=4)
            fixed_sql = str(raw.get("sql", sql)).strip()
            
            # Apply same auto-correct rules for safety
            import re
            if re.search(r'SELECT\s+\*\s+FROM', fixed_sql, re.IGNORECASE) and re.search(r'GROUP\s+BY', fixed_sql, re.IGNORECASE):
                group_match = re.search(r'GROUP\s+BY\s+(.+?)(?:\s+HAVING|\s+ORDER|\s+LIMIT|;|$)', fixed_sql, re.IGNORECASE)
                if group_match:
                    group_cols = group_match.group(1).strip()
                    fixed_sql = re.sub(r'SELECT\s+\*', f'SELECT {group_cols}, COUNT(*) as _count', fixed_sql, flags=re.IGNORECASE)
            
            # Recursive call with retry flag
            return self.execute_with_backup(
                connector, fixed_sql, query_meta, backup_dir, user_query, table_schema, _retry_count=1
            )
            
        exec_time = round(time.time() - start, 3)

        # ── Step 3: Measure rows affected ─────────────────────────
        rows_affected = len(result_df) if result_df is not None else 0

        exec_result = {
            "success":        error is None,
            "result_df":      result_df,
            "rows_affected":  rows_affected,
            "backups":        backups,
            "error":          error,
            "execution_time": exec_time,
            "sql":            sql,
        }

        # Append to audit log
        if self.query_history:
            self.query_history[-1]["execution"] = exec_result

        return exec_result

    # ─────────────────────────────────────────────────────────────
    # Specialized queries: duplicates, nulls, stats
    # ─────────────────────────────────────────────────────────────
    def suggest_cleaning_queries(
        self,
        table_schema: dict,
        db_type: str = "PostgreSQL",
    ) -> List[dict]:
        """
        Ask the LLM to suggest useful data quality / cleaning queries
        based on the table schema.
        Returns a list of {label, sql, category} dicts.
        """
        table_name = table_schema.get("table", "unknown")
        columns    = table_schema.get("columns", [])
        col_names  = [c["name"] for c in columns]

        system_prompt = (
            f"You are an expert data quality analyst and {db_type} SQL engineer.\n"
            f"Given the table '{table_name}' with columns: {col_names},\n"
            "generate 8-12 practical SQL queries for data quality checking and cleaning.\n\n"
            "Categories to cover:\n"
            "  - Duplicate detection\n"
            "  - Missing value analysis\n"
            "  - Data distribution summary\n"
            "  - Outlier / range violations\n"
            "  - Format validation (emails, phones)\n"
            "  - Data freshness / recency\n\n"
            "Return ONLY a JSON array:\n"
            '[\n'
            '  {"label": "Find duplicate emails", "sql": "SELECT ...", "category": "Duplicates"},\n'
            '  ...\n'
            ']'
        )

        user_prompt = (
            f"Table: {table_name}\n"
            f"Columns: {json.dumps(col_names)}\n"
            f"DB type: {db_type}\n\n"
            "Generate data quality queries:"
        )

        raw = self.llm_client.chat_completion_json(
            system_prompt, user_prompt,
            num_expected_keys=12,
            enable_thinking=False,
        )

        if isinstance(raw, list):
            return [q for q in raw if isinstance(q, dict) and "sql" in q]
        elif isinstance(raw, dict):
            # Sometimes LLM wraps the array in an object, e.g. {"queries": [...]}
            for val in raw.values():
                if isinstance(val, list):
                    return [q for q in val if isinstance(q, dict) and "sql" in q]
                    
        return self._default_suggestions(table_name, columns, db_type)

    def _default_suggestions(self, table_name: str, columns: list, db_type: str) -> List[dict]:
        """Fallback hardcoded suggestions when LLM is unavailable."""
        distinct_col = f'"{columns[0]["name"]}"' if columns else "1"
        cols_grp = ', '.join([f'"{c["name"]}"' for c in columns[:3]]) if columns else "1"
        
        suggestions = [
            {
                "label":    "Find all duplicate rows",
                "category": "Duplicates",
                "sql":      f"""SELECT {cols_grp}, COUNT(*) as duplicate_count
FROM "{table_name}"
GROUP BY {cols_grp}
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC""",
            },
            {
                "label":    "Count missing values per column",
                "category": "Missing Values",
                "sql":      "\nUNION ALL\n".join([
                    f"SELECT '{c['name']}' as column_name, COUNT(*) as null_count FROM \"{table_name}\" WHERE \"{c['name']}\" IS NULL"
                    for c in columns[:8]
                ]),
            },
            {
                "label":    "Dataset summary statistics",
                "category": "Overview",
                "sql":      f'SELECT COUNT(*) as total_rows, COUNT(DISTINCT {distinct_col}) as unique_count FROM "{table_name}"',
            },
        ]
        return suggestions

    # ─────────────────────────────────────────────────────────────
    # Query history / audit log
    # ─────────────────────────────────────────────────────────────
    def get_audit_log(self) -> List[dict]:
        """Return a clean audit log without the raw DataFrames."""
        log = []
        for entry in self.query_history:
            clean = {k: v for k, v in entry.items() if k != "result_df"}
            if "execution" in clean:
                exec_copy = {k: v for k, v in clean["execution"].items() if k != "result_df"}
                clean["execution"] = exec_copy
            log.append(clean)
        return log
