
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from src.config import LOG_FILE

def log_query(question: str, sql_query: str, success: bool, error_message: str = None) -> None:
    """Logs the user query, generated SQL, and execution status."""
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "sql_query": sql_query,
        "success": success,
        "error_message": error_message
    }

    logs = get_logs()
    logs.append(entry)

    try:
        with open(LOG_FILE, "w", encoding='utf-8') as f:
            json.dump(logs, f, indent=4)
    except Exception as e:
        print(f"Failed to write logs: {e}")

def get_logs() -> List[Dict]:
    """Retrieves the history of queries."""
    if not os.path.exists(LOG_FILE):
        return []
    
    try:
        with open(LOG_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []
    except Exception as e:
        print(f"Failed to read logs: {e}")
        return []
        
def clear_logs() -> None:
    """Clears all query logs."""
    try:
        with open(LOG_FILE, "w", encoding='utf-8') as f:
            json.dump([], f, indent=4)
    except Exception as e:
        print(f"Failed to clear logs: {e}")
