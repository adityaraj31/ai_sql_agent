
import sqlite3
import re
from typing import List, Tuple, Optional, Dict, Any
from src.config import DB_PATH

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

def run_sql_query(query: str, db_path: str = str(DB_PATH)) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Executes a SQL query against the SQLite database.
    
    Args:
        query (str): The SQL query to execute.
        db_path (str): Path to the SQLite database.

    Returns:
        Tuple[Optional[List[Dict[str, Any]]], Optional[str]]: A tuple containing results (as list of dicts) 
                                                              and error message (if any).
    """
    # Step 1: Validate Safety
    safety_error = validate_sql_safety(query)
    if safety_error:
        return None, safety_error

    try:
        # Use context manager for connection to ensure closure
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            
            # Fetch results
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                results = [dict(zip(columns, row)) for row in rows]
                return results, None
            else:
                # If no description, it might be a query that returns no rows but is valid?
                # But since we restricted to SELECT, it should have description.
                # However, PRAGMA or EXPLAIN might behave differently or return empty?
                return [], None 

    except sqlite3.Error as e:
        return None, str(e)
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def get_db_schema(db_path: str = str(DB_PATH)) -> Dict[str, List[str]]:
    """
    Retrieves the schema (table names and columns) from the database.
    Useful for verification or non-vector context.
    """
    schema = {}
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table});")
                columns = cursor.fetchall()
                # col[1] is name, col[2] is type
                schema[table] = [f"{col[1]} ({col[2]})" for col in columns]
    except Exception as e:
        print(f"Error fetching schema: {e}")
    return schema
