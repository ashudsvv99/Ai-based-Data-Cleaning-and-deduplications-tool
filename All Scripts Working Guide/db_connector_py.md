# `db_connector.py` - The Live Database Orchestrator

The `backend/db_connector.py` script serves as the bridge between the IntelliClean framework and external Live SQL Databases. It replaces the traditional CSV/Excel file upload mechanism with a direct connection to enterprise data warehouses.

## Full Working Process & Logic

### 1. Unified Connection Interface
- **Problem**: Different databases (MySQL, PostgreSQL, SQL Server, Oracle) require entirely different connection strings and drivers (e.g., `pymysql`, `psycopg2`, `pyodbc`).
- **Solution**: The script leverages `sqlalchemy` as a unified Object Relational Mapper (ORM) engine. The `DatabaseConnector` class accepts a standard set of credentials (host, port, user, password, dbname, type) and dynamically formats the correct SQLAlchemy `create_engine` URI based on the selected database type.

### 2. Connection Pooling & Resource Management
- **Problem**: Opening and closing database connections for every single query is highly inefficient and can overload the database server.
- **Solution**: The script utilizes SQLAlchemy's built-in connection pooling mechanism. It maintains an active session, allowing the application to execute multiple queries (e.g., fetching schemas, running profiling, executing AI queries) without needing to handshake with the database server multiple times.

### 3. Schema & Metadata Extraction
- **Action**: Once connected, the `get_tables()` and `get_table_schema(table_name)` methods use SQLAlchemy's `inspect()` functionality to dynamically read the database's metadata. 
- It extracts the column names and SQL Data Types (VARCHAR, INT, DATETIME). This information is crucial because the AI (`NLQueryAgent` and `SchemaAgent`) needs to know the exact database structure in order to generate valid SQL queries and imputation strategies.


### Recent Problems & Architectural Fixes
- **Problem 1 (URL Encoding)**: If a user's database password contained special characters (like `@` or `#`), SQLAlchemy would misinterpret the connection string URI and fail the handshake.
- **Fix 1**: Integrated `urllib.parse.quote_plus` to properly encode the password before injecting it into the connection string, ensuring robust authentication.
- **Problem 2 (Regex Anchoring)**: The `is_safe_query` regex filter was too loose. It could accidentally block valid `SELECT` queries if a column name happened to contain a forbidden word (like `column_update`).
- **Fix 2**: Rewrote the regex patterns to use strict word boundary anchors (`\b`), guaranteeing that the system only blocks actual destructive SQL commands (like `DROP` or `DELETE`) without causing false positives on column names.
