import sys
import sqlite3
import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import (
    DB_TYPE,
    DB_PATH,
    POSTGRES_CONNECTION_STRING,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    POSTGRES_DATABASE,
)

# Try to import PostgreSQL connector
try:
    import psycopg2
    from psycopg2 import Error as PostgresError

    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    PostgresError = Exception


def get_db_connection():
    """
    Get a database connection based on configured DB_TYPE.
    Supports SQLite and PostgreSQL (via connection string or individual params).
    """
    if DB_TYPE == "postgres":
        if not POSTGRES_AVAILABLE:
            raise ImportError(
                "psycopg2 is required for PostgreSQL support. Install with: pip install psycopg2-binary"
            )

        try:
            if POSTGRES_CONNECTION_STRING:
                conn = psycopg2.connect(POSTGRES_CONNECTION_STRING)
                print(f"✅ Connected to PostgreSQL via connection string")
            else:
                conn = psycopg2.connect(
                    host=POSTGRES_HOST,
                    port=POSTGRES_PORT,
                    user=POSTGRES_USER,
                    password=POSTGRES_PASSWORD,
                    database=POSTGRES_DATABASE,
                )
                print(
                    f"✅ Connected to PostgreSQL: {POSTGRES_USER}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}"
                )
            return conn
        except PostgresError as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {str(e)}")
    else:
        # SQLite (default)
        conn = sqlite3.connect(str(DB_PATH))
        print(f"✅ Connected to SQLite: {DB_PATH}")
        return conn


def validate_sql_safety(query: str) -> Optional[str]:
    """
    Checks if the SQL query is safe (read-only).
    Returns None if safe, otherwise returns an error message.
    """
    forbidden_keywords = [
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "INSERT",
        "CREATE",
        "REPLACE",
        "TRUNCATE",
        "GRANT",
        "REVOKE",
    ]

    # Clean the query for checking
    # Remove leading/trailing whitespace
    query_upper = query.strip().upper()

    # Check if valid starting keyword
    allowed_starts = ("SELECT", "WITH", "EXPLAIN")
    if not query_upper.startswith(allowed_starts):
        return (
            "Safety Violation: Only SELECT, WITH, and EXPLAIN statements are allowed."
        )

    # Check for chained destructive commands
    # Look for semicolon followed by forbidden keywords
    # This regex looks for: semicolon, optional whitespace, forbidden keyword, word boundary
    pattern = r";\s*(" + "|".join(forbidden_keywords) + r")\b"
    if re.search(pattern, query_upper):
        return "Safety Violation: Potentially destructive chained command detected."

    return None


def execute_query_sqlite(
    cursor, query: str
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Execute query on SQLite and return results."""
    try:
        cursor.execute(query)

        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]
            return results, None
        else:
            return [], None
    except sqlite3.Error as e:
        return None, str(e)
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


def execute_query_postgres(
    cursor, query: str
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Execute query on PostgreSQL and return results."""
    try:
        cursor.execute(query)

        # Get column names from cursor description
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]
            return results, None
        else:
            return [], None
    except PostgresError as e:
        return None, str(e)
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


def run_sql_query(query: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Executes a SQL query against the configured database (SQLite or PostgreSQL).

    Args:
        query (str): The SQL query to execute.

    Returns:
        Tuple[Optional[List[Dict[str, Any]]], Optional[str]]: A tuple containing results (as list of dicts)
                                                              and error message (if any).
    """
    # Step 1: Validate Safety
    safety_error = validate_sql_safety(query)
    if safety_error:
        return None, safety_error

    try:
        conn = get_db_connection()

        if DB_TYPE == "postgres":
            cursor = conn.cursor()
            results, error = execute_query_postgres(cursor, query)
        else:  # SQLite
            cursor = conn.cursor()
            results, error = execute_query_sqlite(cursor, query)

        conn.close()
        return results, error

    except ConnectionError as e:
        return None, f"Database connection error: {str(e)}"
    except Exception as e:
        return None, f"Database error: {str(e)}"


def get_db_schema() -> Dict[str, List[str]]:
    """
    Retrieves the schema (table names and columns) from the configured database.
    Supports SQLite and PostgreSQL.

    Returns:
        Dict with table names as keys and list of columns as values.
    """
    schema = {}

    try:
        conn = get_db_connection()

        if DB_TYPE == "postgres":
            cursor = conn.cursor()
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                cursor.execute(
                    f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position"
                )
                columns = cursor.fetchall()
                schema[table] = [f"{col[0]} ({col[1]})" for col in columns]
        else:  # SQLite
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                cursor.execute(f"PRAGMA table_info({table});")
                columns = cursor.fetchall()
                # col[1] is name, col[2] is type
                schema[table] = [f"{col[1]} ({col[2]})" for col in columns]

        conn.close()

    except Exception as e:
        print(f"Error fetching schema: {e}")

    return schema
