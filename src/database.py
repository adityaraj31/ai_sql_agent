import sys
import sqlite3
import re
import logging
import threading
from decimal import Decimal
from datetime import date, datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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

try:
    import psycopg2
    from psycopg2 import Error as PostgresError
    from psycopg2 import pool

    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    PostgresError = Exception
    pool = None

_postgres_pool = None
_pool_lock = threading.Lock()


# ─────────────────────────────────────────────────────────────────────────────
# Serialization fix
# ─────────────────────────────────────────────────────────────────────────────
def _serialize_value(value: Any) -> Any:
    """
    Convert psycopg2 types that are not JSON-serializable into plain Python types.

    Root cause of Bug 2: PostgreSQL NUMERIC/DECIMAL columns come back as
    Python Decimal objects, and DATE/TIMESTAMP columns come back as date/datetime.
    Neither is handled by the default JSON encoder, so json.dumps() in
    logger.add_message() raised 'Object of type Decimal is not JSON serializable'.
    """
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _serialize_value(v) for k, v in row.items()}


# ─────────────────────────────────────────────────────────────────────────────
# Connection pool
# ─────────────────────────────────────────────────────────────────────────────
def _init_postgres_pool():
    global _postgres_pool
    if _postgres_pool is not None:
        return _postgres_pool

    with _pool_lock:
        if _postgres_pool is not None:
            return _postgres_pool

        if POSTGRES_CONNECTION_STRING:
            _postgres_pool = pool.ThreadedConnectionPool(
                minconn=2, maxconn=10, dsn=POSTGRES_CONNECTION_STRING
            )
            logger.info("PostgreSQL connection pool initialized (via connection string)")
        else:
            _postgres_pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database=POSTGRES_DATABASE,
            )
            logger.info(
                "PostgreSQL connection pool initialized: "
                "%s@%s:%s/%s", POSTGRES_USER, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DATABASE
            )

    return _postgres_pool


def get_db_connection():
    if DB_TYPE == "postgres":
        if not POSTGRES_AVAILABLE:
            raise ImportError(
                "psycopg2 is required for PostgreSQL. Install: pip install psycopg2-binary"
            )
        try:
            return _init_postgres_pool().getconn()
        except PostgresError as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")
    else:
        conn = sqlite3.connect(str(DB_PATH))
        logger.debug("Connected to SQLite: %s", DB_PATH)
        return conn


def release_connection(conn):
    if DB_TYPE == "postgres" and conn and _postgres_pool:
        _postgres_pool.putconn(conn)


def close_all_pools():
    global _postgres_pool
    if _postgres_pool:
        _postgres_pool.closeall()
        _postgres_pool = None
        logger.info("PostgreSQL connection pool closed")


# ─────────────────────────────────────────────────────────────────────────────
# Safety validation
# ─────────────────────────────────────────────────────────────────────────────
def validate_sql_safety(query: str) -> Optional[str]:
    forbidden = [
        "UPDATE", "DELETE", "DROP", "ALTER", "INSERT",
        "CREATE", "REPLACE", "TRUNCATE", "GRANT", "REVOKE",
    ]
    query_upper = query.strip().upper()
    if not query_upper.startswith(("SELECT", "WITH", "EXPLAIN")):
        return "Safety Violation: Only SELECT, WITH, and EXPLAIN statements are allowed."
    pattern = r";\s*(" + "|".join(forbidden) + r")\b"
    if re.search(pattern, query_upper):
        return "Safety Violation: Potentially destructive chained command detected."
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Query execution
# ─────────────────────────────────────────────────────────────────────────────
def execute_query_sqlite(cursor, query: str) -> Tuple[Optional[List[Dict]], Optional[str]]:
    try:
        cursor.execute(query)
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()], None
        return [], None
    except sqlite3.Error as e:
        return None, str(e)
    except Exception as e:
        return None, f"Unexpected error: {e}"


def execute_query_postgres(cursor, query: str) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """
    Execute a PostgreSQL query and return JSON-safe results.

    The _serialize_row call converts Decimal → float and date/datetime → ISO
    string so that downstream json.dumps() (in logger.add_message) never raises
    'Object of type Decimal is not JSON serializable'.
    """
    try:
        cursor.execute(query)
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            results = [_serialize_row(dict(zip(columns, row))) for row in rows]
            return results, None
        return [], None
    except PostgresError as e:
        return None, str(e)
    except Exception as e:
        return None, f"Unexpected error: {e}"


def run_sql_query(query: str) -> Tuple[Optional[List[Dict]], Optional[str]]:
    safety_error = validate_sql_safety(query)
    if safety_error:
        return None, safety_error

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if DB_TYPE == "postgres":
            return execute_query_postgres(cursor, query)
        else:
            return execute_query_sqlite(cursor, query)
    except ConnectionError as e:
        return None, f"Database connection error: {e}"
    except Exception as e:
        return None, f"Database error: {e}"
    finally:
        if conn:
            if DB_TYPE == "postgres":
                release_connection(conn)
            else:
                conn.close()


def get_db_schema() -> Dict[str, List[str]]:
    schema = {}
    conn = None
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
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_name = %s ORDER BY ordinal_position",
                    (table,),
                )
                schema[table] = [f"{col[0]} ({col[1]})" for col in cursor.fetchall()]
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            for (table,) in cursor.fetchall():
                cursor.execute(f"PRAGMA table_info({table});")
                schema[table] = [f"{col[1]} ({col[2]})" for col in cursor.fetchall()]
    except Exception as e:
        logger.error("Error fetching schema: %s", e)
    finally:
        if conn:
            if DB_TYPE == "postgres":
                release_connection(conn)
            else:
                conn.close()
    return schema