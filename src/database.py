
import sqlite3
import re
from typing import List, Tuple, Optional, Dict, Any
from src.config import DB_TYPE, DB_PATH, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

# Try to import MySQL connector
try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    MySQLError = Exception

def get_db_connection():
    """
    Get a database connection based on configured DB_TYPE.
    Supports both SQLite and MySQL.
    """
    if DB_TYPE == "mysql":
        if not MYSQL_AVAILABLE:
            raise ImportError("mysql-connector-python is required for MySQL support. Install with: pip install mysql-connector-python")
        
        try:
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DATABASE
            )
            print(f"✅ Connected to MySQL: {MYSQL_USER}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")
            return conn
        except MySQLError as e:
            raise ConnectionError(f"Failed to connect to MySQL: {str(e)}")
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
        "UPDATE", "DELETE", "DROP", "ALTER", "INSERT", 
        "CREATE", "REPLACE", "TRUNCATE", "GRANT", "REVOKE"
    ]
    
    # Clean the query for checking
    # Remove leading/trailing whitespace
    query_upper = query.strip().upper()
    
    # Check if valid starting keyword
    allowed_starts = ("SELECT", "WITH", "PRAGMA", "EXPLAIN")
    if not any(query_upper.startswith(keyword) for keyword in allowed_starts):
        return "Safety Violation: Only SELECT, WITH, PRAGMA, and EXPLAIN statements are allowed."
        
    # Check for chained destructive commands
    # Look for semicolon followed by forbidden keywords
    # This regex looks for: semicolon, optional whitespace, forbidden keyword, word boundary
    pattern = r";\s*(" + "|".join(forbidden_keywords) + r")\b"
    if re.search(pattern, query_upper):
        return "Safety Violation: Potentially destructive chained command detected."
        
    return None

def execute_query_sqlite(cursor, query: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
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

def execute_query_mysql(cursor, query: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Execute query on MySQL and return results."""
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
    except MySQLError as e:
        return None, str(e)
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def run_sql_query(query: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Executes a SQL query against the configured database (SQLite or MySQL).
    
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
        
        if DB_TYPE == "mysql":
            cursor = conn.cursor(dictionary=True)
            results, error = execute_query_mysql(cursor, query)
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
    Supports both SQLite and MySQL.
    
    Returns:
        Dict with table names as keys and list of columns as values.
    """
    schema = {}
    
    try:
        conn = get_db_connection()
        
        if DB_TYPE == "mysql":
            cursor = conn.cursor()
            # Get table names from MySQL
            cursor.execute(f"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{MYSQL_DATABASE}'")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f"SELECT COLUMN_NAME, COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{MYSQL_DATABASE}' AND TABLE_NAME = '{table}'")
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
        print(f"❌ Error fetching schema: {e}")
    
    return schema
