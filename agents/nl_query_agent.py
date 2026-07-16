"""
NL Query Agent v2 — Converts natural language queries into SQL,
evaluates safety, manages backups, auto-executes queries, and maintains
multi-turn conversation history.

Workflow:
  1. User types natural language (e.g. "show me duplicate records",
     "which customers have missing emails?", "delete rows where name is blank")
  2. LLM generates a SQL statement with explanation
  3. READ queries → auto-execute immediately, return results
  4. If the SQL is destructive (UPDATE/DELETE/INSERT/DROP/TRUNCATE):
       a. Detect the affected table(s)
       b. Create an automatic backup (table-copy + CSV)
       c. Return a "pending_confirmation" result (UI shows permission modal)
       d. User clicks Confirm → execute_confirmed() runs it
  5. Full audit log of every query session
  6. Conversation history enables multi-turn context (follow-up questions)
  7. Table relationship discovery from FK constraints + naming heuristics

Common NL → SQL examples supported:
  - "check for duplicate records"           → SELECT with GROUP BY + HAVING COUNT > 1
  - "find missing email addresses"          → SELECT WHERE email IS NULL
  - "delete rows with no name"             → DELETE (requires confirmation)
  - "show top 10 customers by revenue"     → SELECT ... ORDER BY ... LIMIT 10
  - "which tables reference orders table?" → relationship discovery
  - "how many unique customers do we have?" → SELECT COUNT(DISTINCT ...)
"""
import re
import json
import datetime
from typing import Optional, Tuple, List, Dict, Any

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
    "average", "sum", "group", "distinct", "unique", "describe",
    "tell me", "give me", "all rows", "sample", "preview",
]

_WRITE_INTENTS = [
    "delete", "remove", "drop", "update", "set", "change", "replace",
    "insert", "add", "create", "truncate", "alter", "merge",
    "clean", "fix", "correct", "modify", "rename", "wipe", "purge",
]


def _classify_intent(user_query: str) -> str:
    ql = user_query.lower()
    if any(w in ql for w in _WRITE_INTENTS):
        return "write"
    return "read"


# ─────────────────────────────────────────────────────────────
# NL Query Agent
# ─────────────────────────────────────────────────────────────
class NLQueryAgent:
    """
    Translates natural language queries into SQL using the local LLM.
    Handles safety checks, backups, and execution.

    Key v2 improvements:
    - conversation_history: multi-turn context (follow-up questions work)
    - Auto-execute READ queries without user intervention
    - Destructive queries return pending_confirmation=True (UI shows modal)
    - discover_relationships(): maps FK + column-name similarity
    - profile_database(): LLM generates a natural-language DB overview
    - suggest_followup_queries(): 3 context-aware follow-up suggestions
    """

    def __init__(self, llm_client: LMStudioClient = None):
        self.llm_client = llm_client or LMStudioClient()
        self.query_history: List[dict] = []
        self.conversation_history: List[dict] = []   # Multi-turn NLP context

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
        all_tables_schemas: List[dict] = None,
        active_table: str = None,
    ) -> dict:
        """
        Convert natural language to SQL using the LLM.
        Returns:
        {
          "sql":                  "<generated SQL>",
          "explanation":          "<plain-english explanation>",
          "is_destructive":       bool,
          "pending_confirmation": bool,   # True if destructive — UI must ask
          "affected_tables":      [...],
          "intent_type":          "read" | "write",
          "safety_warning":       "<message if destructive>",
          "confidence":           "High" | "Medium" | "Low",
          "show_sql":             False,  # hidden by default in UI
        }
        """
        table_name = table_schema.get("table", active_table or "unknown")
        columns    = table_schema.get("columns", [])
        row_count  = table_schema.get("row_count", "?")
        pk_cols    = table_schema.get("pk_columns", [])

        col_desc = "\n".join(
            f"  - {c['name']} ({c['type']}) {'[PK]' if c['name'] in pk_cols else ''}"
            for c in columns
        )

        # Build multi-table schema context
        other_tables_desc = ""
        if all_tables_schemas:
            parts = []
            for ts in all_tables_schemas:
                if ts.get("table") != table_name:
                    t_cols = ", ".join(c["name"] for c in ts.get("columns", []))
                    parts.append(f"  Table '{ts['table']}': {t_cols}")
            if parts:
                other_tables_desc = "Other tables in this database:\n" + "\n".join(parts)

        # Build conversation context
        conv_context = ""
        if self.conversation_history:
            recent = self.conversation_history[-4:]  # last 4 turns
            conv_context = "Recent conversation context:\n"
            for turn in recent:
                role = "User" if turn["role"] == "user" else "SQL"
                conv_context += f"  {role}: {turn['content'][:120]}\n"

        system_prompt = (
            f"You are an expert {db_type} SQL engineer and data analyst.\n"
            f"Database table: '{table_name}' ({row_count} rows)\n\n"
            f"Table schema:\n{col_desc}\n\n"
        )
        if other_tables_desc:
            system_prompt += f"{other_tables_desc}\n\n"
        if sample_data:
            system_prompt += f"Sample rows from '{table_name}':\n{sample_data}\n\n"
        if conv_context:
            system_prompt += f"{conv_context}\n"
        system_prompt += (
            f"Database dialect: {db_type}. {dialect_notes}\n\n"
            "TASK: Convert the user's natural language query into correct, optimized SQL.\n\n"
            "CRITICAL RULES:\n"
            "1. ONLY reference columns that exist in the schema above. Never hallucinate columns. CRITICAL: Do NOT use 'id' if it is not explicitly listed in the schema.\n"
            "2. GROUP BY: when using GROUP BY, always SELECT the grouped columns alongside aggregates. Use valid syntax like COUNT(*) (never empty COUNT()).\n"
            "3. NULL checks: use 'IS NULL' or 'IS NOT NULL'. Use TRIM(col) = '' for empty strings.\n"
            "4. DESTRUCTIVE ops: always include a strict WHERE clause. Never modify entire tables.\n"
            "5. QUOTING: PostgreSQL/Oracle → double-quotes; MySQL → backticks; SQL Server → [].\n"
            "6. DERIVED TABLES (CRITICAL): In MySQL, EVERY derived table (a subquery in the FROM clause) MUST have an alias! Example: SELECT col FROM (SELECT col FROM t) AS t1. DO NOT forget the 'AS t1'!\n"
            "7. EXACT DUPLICATES: If asked to find exact duplicates, DO NOT include the Primary Key [PK] column in your SELECT or GROUP BY. Group by all other data columns and use HAVING COUNT(*) > 1.\n"
            "8. OUTPUT: Return ONLY a raw JSON object (no markdown, no code blocks).\n\n"
            "Return this exact JSON:\n"
            '{\n'
            '  "sql": "<clean SQL statement>",\n'
            '  "explanation": "<plain-English description of what this query does>",\n'
            '  "confidence": "High" | "Medium" | "Low",\n'
            '  "safety_note": "<detailed warning if query modifies data, else empty string>"\n'
            '}'
        )

        user_prompt = f"Natural language query: {user_query}\n\nOUTPUT JSON:"

        raw = self.llm_client.chat_completion_json(
            system_prompt, user_prompt,
            num_expected_keys=4,
            enable_thinking=True,
        )

        if isinstance(raw, list) and len(raw) > 0:
            raw = raw[0]

        if not isinstance(raw, dict) or "sql" not in raw:
            sql = str(raw) if raw else f'SELECT * FROM "{table_name}" LIMIT 100'
            raw = {"sql": sql, "explanation": "LLM returned unexpected format.", "confidence": "Low", "safety_note": ""}

        sql         = str(raw.get("sql", "")).strip()
        sql         = self._auto_fix_group_by(sql)
        sql         = self._auto_fix_derived_tables(sql)
        explanation = str(raw.get("explanation", "")).strip()
        confidence  = str(raw.get("confidence", "Medium")).strip()
        safety_note = str(raw.get("safety_note", "")).strip()

        is_dest     = _detect_destructive(sql)
        affected    = _extract_table_names(sql) if is_dest else []
        intent      = _classify_intent(user_query)

        safety_warning = ""
        if is_dest:
            safety_warning = (
                f"⚠️ This query will MODIFY DATA ({', '.join(affected or [table_name])}).\n"
                "A backup will be created automatically before execution."
            )
            if safety_note:
                safety_warning += f"\nNote: {safety_note}"

        result = {
            "sql":                  sql,
            "explanation":          explanation,
            "is_destructive":       is_dest,
            "pending_confirmation": is_dest,   # UI must show confirm modal
            "affected_tables":      affected if affected else ([table_name] if is_dest else []),
            "intent_type":          intent,
            "safety_warning":       safety_warning,
            "confidence":           confidence,
            "show_sql":             False,      # hidden by default in UI
        }

        # Update conversation history
        self.conversation_history.append({"role": "user",      "content": user_query})
        self.conversation_history.append({"role": "assistant",  "content": f"SQL: {sql}\n{explanation}"})
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        self.query_history.append({
            "timestamp":  datetime.datetime.now().isoformat(),
            "user_query": user_query,
            **result,
        })

        return result

    # ─────────────────────────────────────────────────────────────
    # Execute with backup protection
    # ─────────────────────────────────────────────────────────────
    def execute_with_backup(
        self,
        connector,
        sql: str,
        query_meta: dict,
        backup_dir: str = ".",
        user_query: str = "",
        table_schema: dict = None,
        _retry_count: int = 0,
    ) -> dict:
        """
        Execute SQL safely:
        - If destructive: backup all affected tables first, then execute
        - Returns comprehensive result dict
        """
        import time
        start   = time.time()
        backups = []

        is_dest         = query_meta.get("is_destructive", _detect_destructive(sql))
        affected_tables = query_meta.get("affected_tables", _extract_table_names(sql))

        # ── Step 1: Create backups if destructive ────────────────
        if is_dest and affected_tables:
            for tbl in affected_tables:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                ok_tbl, backup_tbl = connector.create_backup(tbl, ts)
                ok_csv,  csv_path  = connector.create_backup_csv(tbl, backup_dir)
                backups.append({
                    "table":        tbl,
                    "backup_table": backup_tbl if ok_tbl else None,
                    "csv_path":     csv_path   if ok_csv else None,
                    "table_ok":     ok_tbl,
                    "csv_ok":       ok_csv,
                })

        # ── Step 2: Execute SQL ──────────────────────────────────
        result_df, error = connector.execute_query(sql)

        # ── Step 2b: Auto-Retry on DB Error ─────────────────────
        if error is not None and _retry_count < 1 and user_query and table_schema:
            print(f"[NLQueryAgent] Execution failed: {error}. Attempting auto-retry...")
            cols_list = ", ".join([c["name"] for c in table_schema.get("columns", [])]) if isinstance(table_schema, dict) else str(table_schema)
            tbl_name = table_schema.get("table", "unknown") if isinstance(table_schema, dict) else "unknown"

            system_prompt = (
                f"You previously generated this SQL:\n{sql}\n\n"
                f"It failed with this error:\n{error}\n\n"
                f"Fix the SQL using ONLY the valid columns from the '{tbl_name}' table:\n"
                f"Valid columns: {cols_list}\n\n"
                "CRITICAL RULES:\n"
                "1. DO NOT use columns like 'id' if they are not explicitly listed in the valid columns list.\n"
                "2. Ensure aggregate functions are valid (e.g. use COUNT(*), never COUNT()).\n"
                "3. If the error is about a derived table missing an alias, you MUST append 'AS t1' immediately after the subquery's closing parenthesis.\n"
                "Return ONLY the fixed SQL inside the JSON structure."
            )
            raw = self.llm_client.chat_completion_json(system_prompt, user_query, num_expected_keys=4)
            if isinstance(raw, dict):
                fixed_sql = str(raw.get("sql", sql)).strip()
            elif isinstance(raw, list) and len(raw) > 0:
                item = raw[0]
                if isinstance(item, dict):
                    fixed_sql = str(item.get("sql", sql)).strip()
                else:
                    fixed_sql = str(item).strip()
            else:
                fixed_sql = str(raw) if raw else sql
            fixed_sql = self._auto_fix_group_by(fixed_sql)
            fixed_sql = self._auto_fix_derived_tables(fixed_sql)
            return self.execute_with_backup(
                connector, fixed_sql, query_meta, backup_dir, user_query, table_schema, _retry_count=1
            )

        exec_time     = round(time.time() - start, 3)
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

        if self.query_history:
            self.query_history[-1]["execution"] = exec_result

        return exec_result

    # ─────────────────────────────────────────────────────────────
    # Relationship discovery
    # ─────────────────────────────────────────────────────────────
    def discover_relationships(
        self,
        connector,
        all_tables_schemas: List[dict],
        log=print,
    ) -> List[dict]:
        """
        Discover FK relationships and column-name similarity links between tables.
        Returns a list of relationship edges:
        [
          {"from_table": "orders", "from_col": "customer_id",
           "to_table": "customers", "to_col": "customer_id",
           "type": "FK" | "Inferred"},
          ...
        ]
        """
        relationships = []

        # Pass 1: SQLAlchemy FK constraints
        try:
            from sqlalchemy import inspect
            if connector.engine:
                inspector = inspect(connector.engine)
                for schema_info in all_tables_schemas:
                    tbl = schema_info.get("table")
                    if not tbl:
                        continue
                    try:
                        fks = inspector.get_foreign_keys(tbl)
                        for fk in fks:
                            ref_table = fk.get("referred_table")
                            for local_col, ref_col in zip(
                                fk.get("constrained_columns", []),
                                fk.get("referred_columns", [])
                            ):
                                relationships.append({
                                    "from_table": tbl,
                                    "from_col":   local_col,
                                    "to_table":   ref_table,
                                    "to_col":     ref_col,
                                    "type":       "FK",
                                })
                    except Exception:
                        pass
        except Exception:
            pass

        # Pass 2: Column-name heuristic (inferred joins)
        table_col_map = {}
        for schema_info in all_tables_schemas:
            tbl  = schema_info.get("table", "")
            cols = [c["name"] for c in schema_info.get("columns", [])]
            table_col_map[tbl] = cols

        tables = list(table_col_map.keys())
        for i, t1 in enumerate(tables):
            for t2 in tables:
                if t1 == t2:
                    continue
                # t1 is potential parent, t2 is potential child
                for col1 in table_col_map[t1]:
                    for col2 in table_col_map[t2]:
                        c1_low = col1.lower()
                        c2_low = col2.lower()
                        
                        is_match = False
                        # Case A: Exact match and contains id/key/code/ref/no
                        if c1_low == c2_low and any(kw in c1_low for kw in ["id", "key", "code", "ref", "no"]):
                            is_match = True
                            
                        # Case B: t1 has 'id', t2 has 't1_id' or 't1id'
                        elif c1_low == "id" and c2_low in [f"{t1.lower()}_id", f"{t1.lower()}id", f"{t1.rstrip('s').lower()}_id", f"{t1.rstrip('s').lower()}id"]:
                            is_match = True
                            
                        if is_match:
                            # Avoid duplicates (like reverse edges)
                            if not any((r["from_table"] == t1 and r["to_table"] == t2 and r["from_col"] == col1 and r["to_col"] == col2) or 
                                       (r["from_table"] == t2 and r["to_table"] == t1 and r["from_col"] == col2 and r["to_col"] == col1)
                                       for r in relationships):
                                relationships.append({
                                    "from_table": t1,
                                    "from_col":   col1,
                                    "to_table":   t2,
                                    "to_col":     col2,
                                    "type":       "Inferred",
                                })

        log(f"[NLQueryAgent] Discovered {len(relationships)} relationships ({sum(1 for r in relationships if r['type']=='FK')} FK, {sum(1 for r in relationships if r['type']=='Inferred')} inferred).")
        return relationships

    # ─────────────────────────────────────────────────────────────
    # Database profiler (LLM-powered overview)
    # ─────────────────────────────────────────────────────────────
    def profile_database(
        self,
        all_tables_schemas: List[dict],
        db_type: str = "PostgreSQL",
    ) -> str:
        """
        Ask the LLM to generate a natural-language overview of the entire database.
        Returns a markdown string.
        """
        schema_summary = []
        for ts in all_tables_schemas:
            col_names = [c["name"] for c in ts.get("columns", [])]
            schema_summary.append({
                "table":     ts.get("table"),
                "row_count": ts.get("row_count", "?"),
                "columns":   col_names,
            })

        system_prompt = (
            f"You are an expert {db_type} database analyst.\n"
            "Given the database schema below, write a concise, professional overview of:\n"
            "1. What this database appears to store (the domain/purpose)\n"
            "2. A brief description of each table and its role\n"
            "3. Key relationships you can infer\n"
            "4. Data quality concerns (e.g. tables with many nulls, missing FKs)\n\n"
            "Format your response in clean markdown with sections. Be concise (max 300 words)."
        )
        user_prompt = (
            f"Database schema:\n{json.dumps(schema_summary, indent=2, default=str)}\n\n"
            "Write the database overview:"
        )

        raw = self.llm_client.chat_completion_json(
            system_prompt, user_prompt, num_expected_keys=1, enable_thinking=False
        )
        # LLM might return plain text or a JSON object with a "text" key
        if isinstance(raw, str):
            return raw
        if isinstance(raw, dict):
            for k in ["overview", "text", "description", "summary", "content"]:
                if k in raw:
                    return str(raw[k])
            return json.dumps(raw, indent=2)
        return "Database overview unavailable."

    # ─────────────────────────────────────────────────────────────
    # Suggested cleaning queries
    # ─────────────────────────────────────────────────────────────
    def suggest_cleaning_queries(
        self,
        table_schema: dict,
        db_type: str = "PostgreSQL",
    ) -> List[dict]:
        """Ask the LLM to suggest data quality / cleaning queries for the table."""
        table_name = table_schema.get("table", "unknown")
        columns    = table_schema.get("columns", [])
        col_names  = [c["name"] for c in columns]

        system_prompt = (
            f"You are an expert data quality analyst and {db_type} SQL engineer.\n"
            f"Given table '{table_name}' with columns: {col_names},\n"
            "generate 8-12 practical SQL queries for data quality checking and cleaning.\n\n"
            "Categories to cover:\n"
            "  - Duplicate detection\n"
            "  - Missing value analysis\n"
            "  - Data distribution / summary\n"
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
            f"Table: {table_name}\nColumns: {json.dumps(col_names)}\nDB: {db_type}\n\n"
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
            for val in raw.values():
                if isinstance(val, list):
                    return [q for q in val if isinstance(q, dict) and "sql" in q]

        return self._default_suggestions(table_name, columns, db_type)

    # ─────────────────────────────────────────────────────────────
    # Follow-up suggestions
    # ─────────────────────────────────────────────────────────────
    def suggest_followup_queries(
        self,
        user_query: str,
        result_summary: str,
        table_name: str,
    ) -> List[str]:
        """
        After a query result, suggest 3 natural-language follow-up questions.
        These are displayed as clickable chips in the UI.
        """
        system_prompt = (
            "You are a helpful data analyst assistant.\n"
            f"The user asked: '{user_query}'\n"
            f"The result was: {result_summary[:300]}\n\n"
            f"Suggest 3 concise, practical follow-up questions the user might ask about the '{table_name}' table.\n"
            "Return ONLY a JSON array of 3 strings:\n"
            '["question 1", "question 2", "question 3"]'
        )
        raw = self.llm_client.chat_completion_json(
            system_prompt, "Suggest follow-ups:", num_expected_keys=3, enable_thinking=False
        )
        if isinstance(raw, list) and len(raw) >= 1:
            return [str(q) for q in raw[:3]]
        return [
            f"Show the top 10 rows from {table_name}",
            f"Count null values in {table_name}",
            f"Find duplicate rows in {table_name}",
        ]

    # ─────────────────────────────────────────────────────────────
    # Utility: clear conversation
    # ─────────────────────────────────────────────────────────────
    def clear_conversation(self):
        """Reset conversation history (start a new chat session)."""
        self.conversation_history = []

    # ─────────────────────────────────────────────────────────────
    # Audit log
    # ─────────────────────────────────────────────────────────────
    def get_audit_log(self) -> List[dict]:
        """Return audit log without raw DataFrames."""
        log = []
        for entry in self.query_history:
            clean = {k: v for k, v in entry.items() if k != "result_df"}
            if "execution" in clean:
                exec_copy = {k: v for k, v in clean["execution"].items() if k != "result_df"}
                clean["execution"] = exec_copy
            log.append(clean)
        return log

    # ─────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _auto_fix_group_by(sql: str) -> str:
        """Auto-correct GROUP BY queries missing grouped columns in SELECT."""
        if re.search(r'GROUP\s+BY', sql, re.IGNORECASE):
            group_match = re.search(
                r'GROUP\s+BY\s+(.+?)(?:\s+HAVING|\s+ORDER|\s+LIMIT|;|$)', sql, re.IGNORECASE
            )
            if group_match:
                group_cols = group_match.group(1).strip()
                if re.search(r'SELECT\s+\*\s+FROM', sql, re.IGNORECASE):
                    sql = re.sub(
                        r'SELECT\s+\*',
                        f'SELECT {group_cols}, COUNT(*) as count',
                        sql, flags=re.IGNORECASE, count=1
                    )
                else:
                    select_match = re.search(r'SELECT\s+(.+?)\s+FROM', sql, re.IGNORECASE)
                    if select_match:
                        select_str     = select_match.group(1).strip()
                        first_group_col = group_cols.split(',')[0].strip()
                        if first_group_col.lower() not in select_str.lower():
                            new_select = f"{group_cols}, {select_str}"
                            sql = re.sub(
                                r'SELECT\s+(.+?)\s+FROM',
                                f'SELECT {new_select} FROM',
                                sql, flags=re.IGNORECASE, count=1
                            )
        return sql

    @staticmethod
    def _auto_fix_derived_tables(sql: str) -> str:
        """Fix derived tables that are missing an alias in MySQL."""
        return re.sub(
            r'(FROM\s+\(\s*SELECT.+?\))(\s*(?:;|LIMIT|ORDER|GROUP|HAVING|WHERE|$))',
            r'\1 AS t1\2',
            sql,
            flags=re.IGNORECASE | re.DOTALL
        )

    def _default_suggestions(self, table_name: str, columns: list, db_type: str) -> List[dict]:
        """Fallback hardcoded suggestions when LLM is unavailable."""
        distinct_col = f'"{columns[0]["name"]}"' if columns else "1"
        cols_grp = ', '.join([f'"{c["name"]}"' for c in columns[:3]]) if columns else "1"
        return [
            {
                "label":    "Find all duplicate rows",
                "category": "Duplicates",
                "sql":      f'SELECT {cols_grp}, COUNT(*) as duplicate_count\nFROM "{table_name}"\nGROUP BY {cols_grp}\nHAVING COUNT(*) > 1\nORDER BY duplicate_count DESC',
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
