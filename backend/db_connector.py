"""
Universal Database Connector — supports PostgreSQL, MySQL, SQLite,
Microsoft SQL Server, Oracle DB, and IBM DB2.

Features:
  - Unified connect/disconnect/test interface
  - Schema discovery (list databases, tables, columns, row counts)
  - Safe query execution with read-only guard
  - Backup creation before any destructive SQL (UPDATE / DELETE / INSERT / DROP / TRUNCATE / ALTER)
  - Write-back: push cleaned DataFrame back into DB table
  - Connection pooling via SQLAlchemy
"""
import re
import json
import datetime
import pandas as pd
from typing import Optional, List, Dict, Any, Tuple


# ─────────────────────────────────────────────────────────────
# Supported database types and their metadata
# ─────────────────────────────────────────────────────────────
DB_TYPES = {
    "PostgreSQL": {
        "icon": "🐘",
        "color": "#336791",
        "description": "Open-source RDBMS",
        "default_port": 5432,
        "driver": "postgresql+psycopg2",
        "pip_package": "psycopg2-binary",
    },
    "MySQL": {
        "icon": "🐬",
        "color": "#00618a",
        "description": "World's most popular OSS DB",
        "default_port": 3306,
        "driver": "mysql+pymysql",
        "pip_package": "pymysql",
    },
    "SQLite": {
        "icon": "📦",
        "color": "#44a0d0",
        "description": "Embedded file database",
        "default_port": None,
        "driver": "sqlite",
        "pip_package": "built-in",
    },
    "SQL Server": {
        "icon": "🗄️",
        "color": "#cc2927",
        "description": "Microsoft RDBMS",
        "default_port": 1433,
        "driver": "mssql+pyodbc",
        "pip_package": "pyodbc",
    },
    "Oracle DB": {
        "icon": "🔴",
        "color": "#f80000",
        "description": "Enterprise RDBMS",
        "default_port": 1521,
        "driver": "oracle+oracledb",
        "pip_package": "oracledb",
    },
    "IBM DB2": {
        "icon": "💙",
        "color": "#1f70c1",
        "description": "Enterprise analytics DB",
        "default_port": 50000,
        "driver": "ibm_db_sa",
        "pip_package": "ibm_db_sa",
    },
    "Snowflake": {
        "icon": "❄️",
        "color": "#29b5e8",
        "description": "Cloud Data Warehouse",
        "default_port": 443,
        "driver": "snowflake",
        "pip_package": "snowflake-sqlalchemy",
    },
    "Amazon Redshift": {
        "icon": "☁️",
        "color": "#c92501",
        "description": "AWS Data Warehouse",
        "default_port": 5439,
        "driver": "redshift+psycopg2",
        "pip_package": "sqlalchemy-redshift",
    },
    "MariaDB": {
        "icon": "🦭",
        "color": "#003545",
        "description": "Open-source RDBMS",
        "default_port": 3306,
        "driver": "mysql+pymysql",
        "pip_package": "pymysql",
    },
}

# SQL operations that are destructive and require a backup
_DESTRUCTIVE_KEYWORDS = re.compile(
    r'^\s*(UPDATE|DELETE|INSERT|DROP|TRUNCATE|ALTER|REPLACE|MERGE|CREATE|RENAME)\b',
    re.IGNORECASE,
)

# SQLAlchemy engine cache: {connection_key: engine}
_ENGINE_CACHE: Dict[str, Any] = {}


def _format_db_error(e: Exception) -> str:
    err_str = str(e).lower()
    if "access denied" in err_str or "authentication failed" in err_str or "password authentication failed" in err_str or "1045" in err_str:
        return "Authentication failed. Please verify your username and password."
    if "unknown database" in err_str or "database does not exist" in err_str or "1049" in err_str:
        return "The specified database does not exist. Please check the database name."
    if "connection refused" in err_str or "could not connect" in err_str or "timeout" in err_str or "2003" in err_str:
        return "Could not connect to the database server. Please verify the host, port, and ensure the server is running."
    return f"Database error: {str(e)}"

def _make_engine(db_type: str, params: dict):
    """
    Create a SQLAlchemy engine for the given DB type and connection params.
    Returns (engine, error_message).
    """
    try:
        from sqlalchemy import create_engine, text
        import sqlalchemy
    except ImportError:
        return None, "SQLAlchemy is not installed. Run: pip install sqlalchemy"

    try:
        import urllib.parse
        
        def _q(val):
            return urllib.parse.quote_plus(str(val)) if val else ""
            
        if db_type == "SQLite":
            filepath = params.get("filepath", ":memory:")
            url = f"sqlite:///{filepath}"
            engine = create_engine(url, connect_args={"check_same_thread": False})

        elif db_type == "PostgreSQL":
            url = (
                f"postgresql+psycopg2://{_q(params['username'])}:{_q(params['password'])}"
                f"@{params['host']}:{params['port']}/{_q(params['database'])}"
            )
            ssl_args = {}
            if params.get("ssl_mode", "disable") != "disable":
                ssl_args = {"sslmode": params["ssl_mode"]}
            engine = create_engine(url, connect_args=ssl_args, pool_size=params.get("pool_size", 5))

        elif db_type == "MySQL":
            url = (
                f"mysql+pymysql://{_q(params['username'])}:{_q(params['password'])}"
                f"@{params['host']}:{params['port']}/{_q(params['database'])}"
            )
            engine = create_engine(url, pool_size=params.get("pool_size", 5))

        elif db_type == "SQL Server":
            driver = params.get("odbc_driver", "ODBC Driver 17 for SQL Server")
            url = (
                f"mssql+pyodbc://{_q(params['username'])}:{_q(params['password'])}"
                f"@{params['host']}:{params['port']}/{_q(params['database'])}"
                f"?driver={driver.replace(' ', '+')}"
            )
            engine = create_engine(url)

        elif db_type == "Oracle DB":
            url = (
                f"oracle+oracledb://{_q(params['username'])}:{_q(params['password'])}"
                f"@{params['host']}:{params['port']}/?service_name={_q(params['database'])}"
            )
            engine = create_engine(url)

        elif db_type == "IBM DB2":
            url = (
                f"ibm_db_sa://{_q(params['username'])}:{_q(params['password'])}"
                f"@{params['host']}:{params['port']}/{_q(params['database'])}"
            )
            engine = create_engine(url)

        elif db_type == "Snowflake":
            url = (
                f"snowflake://{_q(params['username'])}:{_q(params['password'])}"
                f"@{params['host']}/{_q(params['database'])}"
            )
            schema = params.get("schema", "")
            if schema:
                url += f"/{_q(schema)}"
            query_params = []
            if params.get("warehouse"):
                query_params.append(f"warehouse={_q(params['warehouse'])}")
            if params.get("role"):
                query_params.append(f"role={_q(params['role'])}")
            if query_params:
                url += "?" + "&".join(query_params)
            engine = create_engine(url)

        elif db_type == "Amazon Redshift":
            url = (
                f"redshift+psycopg2://{_q(params['username'])}:{_q(params['password'])}"
                f"@{params['host']}:{params['port']}/{_q(params['database'])}"
            )
            engine = create_engine(url)
            
        elif db_type == "MariaDB":
            url = (
                f"mysql+pymysql://{_q(params['username'])}:{_q(params['password'])}"
                f"@{params['host']}:{params['port']}/{_q(params['database'])}"
            )
            engine = create_engine(url, pool_size=params.get("pool_size", 5))

        else:
            return None, f"Unknown DB type: {db_type}"

        # Quick connectivity test
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))

        return engine, None
    except Exception as e:
        return None, _format_db_error(e)


class DatabaseConnector:
    """
    Universal database connector — wraps SQLAlchemy engines with a clean API.
    """

    def __init__(self, db_type: str, params: dict):
        self.db_type = db_type
        self.params  = params
        self.engine  = None
        self.error   = None
        self._connected = False

    # ─────────────────────────────────────────────────────────────
    # Connection management
    # ─────────────────────────────────────────────────────────────
    def connect(self) -> Tuple[bool, str]:
        """Connect to the database. Returns (success, message)."""
        engine, err = _make_engine(self.db_type, self.params)
        if err:
            self.error = err
            self._connected = False
            return False, f"Connection failed: {err}"
        self.engine = engine
        self._connected = True
        return True, f"Connected to {self.db_type} successfully."

    def disconnect(self):
        if self.engine:
            self.engine.dispose()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def test_connection(self) -> Tuple[bool, str]:
        """Test existing connection by running SELECT 1."""
        if not self.engine:
            return False, "No engine — call connect() first."
        try:
            from sqlalchemy import text
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, "Connection is alive."
        except Exception as e:
            self._connected = False
            return False, str(e)

    # ─────────────────────────────────────────────────────────────
    # Schema discovery
    # ─────────────────────────────────────────────────────────────
    def list_tables(self) -> List[str]:
        """Return list of table names in the connected database."""
        if not self.engine:
            return []
        try:
            from sqlalchemy import inspect
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except Exception:
            return []

    def list_schemas(self) -> List[str]:
        """Return list of schemas/databases."""
        if not self.engine:
            return []
        try:
            from sqlalchemy import inspect
            inspector = inspect(self.engine)
            return inspector.get_schema_names()
        except Exception:
            return []

    def get_table_info(self, table_name: str) -> dict:
        """
        Return detailed info about a table:
        columns, dtypes, row count, sample rows, primary keys.
        """
        if not self.engine:
            return {}
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(self.engine)

            columns = []
            for col in inspector.get_columns(table_name):
                columns.append({
                    "name":     col["name"],
                    "type":     str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default":  str(col.get("default", "")),
                })

            pk = inspector.get_pk_constraint(table_name)
            pk_cols = pk.get("constrained_columns", [])
            
            # Fallback: Infer Primary Key if none explicitly defined
            if not pk_cols:
                for col in columns:
                    cname = col["name"].lower()
                    if cname == "id" or cname == f"{table_name.lower()}_id" or cname == f"{table_name.rstrip('s').lower()}_id":
                        pk_cols = [col["name"]]
                        break

            from sqlalchemy import select, func, table
            with self.engine.connect() as conn:
                stmt = select(func.count()).select_from(table(table_name))
                row_count = conn.execute(stmt).scalar()

            return {
                "table":       table_name,
                "columns":     columns,
                "pk_columns":  pk_cols,
                "row_count":   row_count,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_extended_metadata(self) -> dict:
        """
        Fetch extended metadata for Knowledge Graph: 
        schemas, tables, views, columns, keys, indexes, triggers, functions, etc.
        """
        if not self.engine:
            return {}
            
        metadata = {
            "schemas": [], "tables": [], "views": [], "materialized_views": [],
            "columns": [], "primary_keys": [], "foreign_keys": [], "unique_keys": [],
            "indexes": [], "constraints": [], "triggers": [], "functions": [], "stored_procedures": []
        }
        
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(self.engine)
            
            # Schemas
            try:
                metadata["schemas"] = [{"name": s} for s in inspector.get_schema_names()]
            except: pass
                
            # Triggers / Functions (dialect specific)
            try:
                with self.engine.connect() as conn:
                    if self.db_type == "PostgreSQL":
                        res = conn.execute(text("SELECT trigger_name, event_object_table FROM information_schema.triggers"))
                        for row in res:
                            metadata["triggers"].append({"name": row[0], "table": row[1]})
                        res = conn.execute(text("SELECT routine_name, routine_type FROM information_schema.routines WHERE routine_schema NOT IN ('pg_catalog', 'information_schema')"))
                        for row in res:
                            if row[1] == 'PROCEDURE': metadata["stored_procedures"].append({"name": row[0]})
                            else: metadata["functions"].append({"name": row[0]})
                    elif self.db_type in ("MySQL", "MariaDB"):
                        res = conn.execute(text("SHOW TRIGGERS"))
                        for row in res:
                            metadata["triggers"].append({"name": row[0], "table": row[2]})
                        res = conn.execute(text("SHOW FUNCTION STATUS WHERE Db = DATABASE()"))
                        for row in res:
                            metadata["functions"].append({"name": row[1]})
                        res = conn.execute(text("SHOW PROCEDURE STATUS WHERE Db = DATABASE()"))
                        for row in res:
                            metadata["stored_procedures"].append({"name": row[1]})
                    elif self.db_type == "SQL Server":
                        res = conn.execute(text("SELECT name FROM sys.triggers"))
                        for row in res:
                            metadata["triggers"].append({"name": row[0]})
                        res = conn.execute(text("SELECT name, type_desc FROM sys.objects WHERE type IN ('P', 'FN', 'IF', 'TF')"))
                        for row in res:
                            if row[1] == 'SQL_STORED_PROCEDURE': metadata["stored_procedures"].append({"name": row[0]})
                            else: metadata["functions"].append({"name": row[0]})
            except: pass
            
            # Tables & Views
            try:
                tables = inspector.get_table_names()
                metadata["tables"] = [{"name": t} for t in tables]
            except: tables = []
                
            try:
                views = inspector.get_view_names()
                metadata["views"] = [{"name": v} for v in views]
            except: views = []
                
            try:
                mviews = inspector.get_mview_names()
                metadata["materialized_views"] = [{"name": mv} for mv in mviews]
            except: pass
                
            # Detailed metadata per table
            for tname in tables:
                try:
                    for c in inspector.get_columns(tname):
                        metadata["columns"].append({"table": tname, "name": c["name"], "type": str(c["type"])})
                except: pass
                
                try:
                    pk = inspector.get_pk_constraint(tname)
                    if pk and pk.get("constrained_columns"):
                        metadata["primary_keys"].append({"table": tname, "name": pk.get("name") or f"PK_{tname}", "columns": pk["constrained_columns"]})
                except: pass
                
                try:
                    for fk in inspector.get_foreign_keys(tname):
                        metadata["foreign_keys"].append({"table": tname, "name": fk.get("name") or f"FK_{tname}", "referred_table": fk["referred_table"]})
                except: pass
                
                try:
                    for uk in inspector.get_unique_constraints(tname):
                        metadata["unique_keys"].append({"table": tname, "name": uk.get("name") or f"UK_{tname}", "columns": uk["column_names"]})
                except: pass
                
                try:
                    for idx in inspector.get_indexes(tname):
                        metadata["indexes"].append({"table": tname, "name": idx["name"], "columns": idx["column_names"]})
                except: pass
                
                try:
                    for cc in inspector.get_check_constraints(tname):
                        metadata["constraints"].append({"table": tname, "name": cc.get("name") or f"CHK_{tname}"})
                except: pass
                
            return metadata
        except Exception as e:
            return {"error": str(e)}

    # ─────────────────────────────────────────────────────────────
    # Data loading
    # ─────────────────────────────────────────────────────────────
    def load_table(self, table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
        """Load an entire table (or first N rows) into a DataFrame."""
        if not self.engine:
            raise ConnectionError("Not connected.")
            
        # Hard cap to prevent Out-Of-Memory crashes on large tables
        max_limit = 100000
        actual_limit = min(limit, max_limit) if limit else max_limit
        
        try:
            for chunk in pd.read_sql_table(table_name, self.engine, chunksize=actual_limit):
                return chunk
            return pd.DataFrame()
        except Exception:
            try:
                from sqlalchemy import select, table
                stmt = select(table(table_name)).limit(actual_limit)
                return pd.read_sql(stmt, self.engine)
            except Exception as e:
                raise Exception(_format_db_error(e))


    def execute_query(self, sql: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Execute any SQL and return (DataFrame | None, error | None).
        SELECT queries return a DataFrame; others return None.
        """
        if not self.engine:
            return None, "Not connected."
        try:
            from sqlalchemy import text
            sql_stripped = sql.strip()
            is_select = sql_stripped.upper().startswith("SELECT") or sql_stripped.upper().startswith("WITH")
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_stripped))
                if is_select:
                    rows = result.fetchall()
                    cols = list(result.keys())
                    df = pd.DataFrame(rows, columns=cols)
                    return df, None
                else:
                    conn.commit()
                    return None, None
        except Exception as e:
            return None, _format_db_error(e)

    # ─────────────────────────────────────────────────────────────
    # Backup before destructive ops
    # ─────────────────────────────────────────────────────────────
    def is_destructive(self, sql: str) -> bool:
        """Return True if the SQL contains destructive keywords."""
        return bool(_DESTRUCTIVE_KEYWORDS.search(sql))

    def create_backup(self, table_name: str, backup_suffix: str = None) -> Tuple[bool, str]:
        """
        Create a backup of a table as a new table with a timestamp suffix.
        Returns (success, backup_table_name or error_message).
        """
        if not self.engine:
            return False, "Not connected."
        ts = backup_suffix or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{table_name}_backup_{ts}"
        try:
            from sqlalchemy import text
            if self.db_type == "SQLite":
                sql = f'CREATE TABLE "{backup_name}" AS SELECT * FROM "{table_name}"'
            elif self.db_type in ("MySQL", "MariaDB"):
                sql = f'CREATE TABLE `{backup_name}` AS SELECT * FROM `{table_name}`'
            elif self.db_type == "PostgreSQL":
                sql = f'CREATE TABLE "{backup_name}" AS SELECT * FROM "{table_name}"'
            elif self.db_type == "SQL Server":
                sql = f'SELECT * INTO "{backup_name}" FROM "{table_name}"'
            elif self.db_type == "Oracle DB":
                sql = f'CREATE TABLE "{backup_name}" AS SELECT * FROM "{table_name}"'
            else:
                sql = f'CREATE TABLE "{backup_name}" AS SELECT * FROM "{table_name}"'

            with self.engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            return True, backup_name
        except Exception as e:
            return False, str(e)

    def create_backup_csv(self, table_name: str, backup_dir: str = ".") -> Tuple[bool, str]:
        """
        Create a CSV backup of the table. Works for all DB types.
        Returns (success, filepath or error).
        """
        import os
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{table_name}_backup_{ts}.csv"
        filepath = os.path.join(backup_dir, filename)
        try:
            df = self.load_table(table_name)
            df.to_csv(filepath, index=False)
            return True, filepath
        except Exception as e:
            return False, str(e)

    # ─────────────────────────────────────────────────────────────
    # Write-back
    # ─────────────────────────────────────────────────────────────
    def write_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = "replace",   # "replace" | "append" | "fail"
        index: bool = False,
    ) -> Tuple[bool, str]:
        """Write a DataFrame back to the database table."""
        if not self.engine:
            return False, "Not connected."
        try:
            if if_exists == "replace":
                from sqlalchemy import inspect, text
                inspector = inspect(self.engine)
                if inspector.has_table(table_name):
                    # Instead of dropping the table (which breaks foreign keys),
                    # we delete all rows and append within a transaction.
                    with self.engine.connect() as conn:
                        if self.db_type in ("MySQL", "MariaDB"):
                            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
                            conn.commit()
                        
                        with conn.begin():
                            if self.db_type in ("MySQL", "MariaDB"):
                                conn.execute(text(f"DELETE FROM `{table_name}`"))
                            elif self.db_type in ["PostgreSQL", "SQL Server", "Oracle DB", "SQLite", "Amazon Redshift", "Snowflake"]:
                                conn.execute(text(f'DELETE FROM "{table_name}"'))
                            else:
                                conn.execute(text(f"DELETE FROM {table_name}"))
                            
                            df.to_sql(table_name, conn, if_exists="append", index=index)
                            
                        if self.db_type in ("MySQL", "MariaDB"):
                            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
                            conn.commit()
                else:
                    df.to_sql(table_name, self.engine, if_exists="replace", index=index)
            else:
                df.to_sql(table_name, self.engine, if_exists=if_exists, index=index)
                
            return True, f"Written {len(df)} rows to '{table_name}'."
        except Exception as e:
            return False, str(e)

    # ─────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────
    def get_connection_summary(self) -> dict:
        """Return a serializable summary of the connection."""
        p = self.params
        return {
            "db_type":  self.db_type,
            "host":     p.get("host", ""),
            "port":     p.get("port", ""),
            "database": p.get("database", p.get("filepath", "")),
            "username": p.get("username", ""),
            "status":   "connected" if self._connected else "disconnected",
        }
