import sys
import json
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import CHAT_POSTGRES_CONNECTION_STRING

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    import psycopg2
    from psycopg2 import Error as PostgresError
    from psycopg2 import pool

    CHAT_DB_AVAILABLE = True
except ImportError:
    CHAT_DB_AVAILABLE = False
    PostgresError = Exception
    pool = None

_chat_pool = None
_chat_pool_lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────────────────
# Guard flag — tracks whether init_chat_tables() has already succeeded.
#
# Root cause of Bug 3: init_chat_tables() was called once at module import,
# but if the connection wasn't ready yet (or the function silently swallowed
# an error) subsequent calls to get_all_sessions() / create_session() would
# hit "relation chat_sessions does not exist".
#
# Fix: every public function that touches the DB calls _ensure_tables() first.
# _ensure_tables() is a no-op after the first successful run (thread-safe).
# ─────────────────────────────────────────────────────────────────────────────
_tables_initialised = False
_tables_init_lock = threading.Lock()


def _init_chat_pool():
    global _chat_pool
    if _chat_pool is not None:
        return _chat_pool

    with _chat_pool_lock:
        if _chat_pool is not None:
            return _chat_pool

        if not CHAT_POSTGRES_CONNECTION_STRING:
            raise ValueError("CHAT_POSTGRES_CONNECTION_STRING is not set")

        _chat_pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=CHAT_POSTGRES_CONNECTION_STRING,
        )
        logger.info("Chat database connection pool initialized")

    return _chat_pool


def get_chat_db_connection():
    if not CHAT_POSTGRES_CONNECTION_STRING:
        raise ValueError("CHAT_POSTGRES_CONNECTION_STRING is not set")
    if not CHAT_DB_AVAILABLE:
        raise ImportError("psycopg2 is required. Install: pip install psycopg2-binary")
    try:
        return _init_chat_pool().getconn()
    except PostgresError as e:
        raise ConnectionError(f"Failed to connect to chat database: {e}")


def release_chat_connection(conn):
    if conn and _chat_pool:
        _chat_pool.putconn(conn)


def close_chat_pool():
    global _chat_pool
    if _chat_pool:
        _chat_pool.closeall()
        _chat_pool = None
        logger.info("Chat database connection pool closed")


def init_chat_tables() -> bool:
    """
    Create chat_sessions and chat_messages if they don't exist.
    Returns True on success, False on failure.
    """
    if not CHAT_POSTGRES_CONNECTION_STRING:
        return False

    conn = None
    try:
        conn = get_chat_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id         SERIAL PRIMARY KEY,
                session_id TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                title      TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id         SERIAL PRIMARY KEY,
                session_id TEXT,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                sql_query  TEXT,
                results    JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        logger.info("Chat tables ready.")
        return True
    except Exception as e:
        logger.warning("Failed to initialise chat tables: %s", e)
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False
    finally:
        if conn:
            release_chat_connection(conn)


def _ensure_tables():
    """
    Guarantee tables exist before any DML/query.
    Runs init_chat_tables() exactly once (idempotent after first success).
    """
    global _tables_initialised
    if _tables_initialised:
        return
    with _tables_init_lock:
        if _tables_initialised:
            return
        _tables_initialised = init_chat_tables()


def migrate_existing_sessions() -> int:
    """
    Migration: Update existing sessions without titles using their first user message.
    Returns the number of sessions updated.
    """
    if not CHAT_POSTGRES_CONNECTION_STRING:
        return 0
    _ensure_tables()

    from src.rag import generate_session_title

    conn = None
    updated = 0
    try:
        conn = get_chat_db_connection()
        cursor = conn.cursor()

        # Get sessions without titles (NULL or 'New Chat')
        cursor.execute("""
            SELECT s.session_id, m.content
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON m.session_id = s.session_id AND m.role = 'user'
            WHERE s.title IS NULL OR s.title = 'New Chat'
            ORDER BY s.created_at ASC
            LIMIT 100
        """)

        sessions_to_update = cursor.fetchall()

        for session_id, first_message in sessions_to_update:
            if first_message:
                try:
                    title = generate_session_title(first_message)
                    cursor.execute(
                        "UPDATE chat_sessions SET title = %s WHERE session_id = %s",
                        (title, session_id),
                    )
                    updated += 1
                except Exception as e:
                    logger.warning(f"Failed to generate title for {session_id}: {e}")

        conn.commit()
        if updated > 0:
            logger.info(f"Migration: Updated {updated} session titles")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        if conn:
            release_chat_connection(conn)

    return updated


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def create_session(session_id: str, title: str = None) -> None:
    if not CHAT_POSTGRES_CONNECTION_STRING:
        return
    _ensure_tables()
    conn = None
    try:
        conn = get_chat_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO chat_sessions (session_id, title)
            VALUES (%s, %s)
            ON CONFLICT (session_id) DO NOTHING
            """,
            (session_id, title or "New Chat"),
        )
        conn.commit()
    except Exception as e:
        logger.error("Failed to create session: %s", e)
    finally:
        if conn:
            release_chat_connection(conn)


def update_session_title(session_id: str, title: str) -> None:
    """Update the title of an existing session."""
    if not CHAT_POSTGRES_CONNECTION_STRING:
        return
    _ensure_tables()
    conn = None
    try:
        conn = get_chat_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE chat_sessions 
            SET title = %s 
            WHERE session_id = %s
            """,
            (title, session_id),
        )
        conn.commit()
    except Exception as e:
        logger.error("Failed to update session title: %s", e)
    finally:
        if conn:
            release_chat_connection(conn)


def add_message(
    session_id: str,
    role: str,
    content: str,
    sql_query: str = None,
    results: list = None,
) -> None:
    if not CHAT_POSTGRES_CONNECTION_STRING:
        return
    _ensure_tables()
    conn = None
    try:
        conn = get_chat_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO chat_messages (session_id, role, content, sql_query, results)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                session_id,
                role,
                content,
                sql_query,
                json.dumps(results) if results else None,
            ),
        )
        conn.commit()
    except Exception as e:
        logger.error("Failed to add message: %s", e)
    finally:
        if conn:
            release_chat_connection(conn)


def get_session_messages(session_id: str) -> List[Dict]:
    if not CHAT_POSTGRES_CONNECTION_STRING:
        return []
    _ensure_tables()
    conn = None
    try:
        conn = get_chat_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT role, content, sql_query, results, created_at
            FROM chat_messages
            WHERE session_id = %s
            ORDER BY created_at ASC
            """,
            (session_id,),
        )
        columns = [desc[0] for desc in cursor.description]
        messages = []
        for row in cursor.fetchall():
            msg = dict(zip(columns, row))
            if msg.get("results"):
                msg["results"] = json.loads(msg["results"])
            messages.append(msg)
        return messages
    except Exception as e:
        logger.error("Failed to get session messages: %s", e)
        return []
    finally:
        if conn:
            release_chat_connection(conn)


def get_session_message_count(session_id: str) -> int:
    """Get the number of messages in a session."""
    if not CHAT_POSTGRES_CONNECTION_STRING:
        return 0
    _ensure_tables()
    conn = None
    try:
        conn = get_chat_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE session_id = %s",
            (session_id,),
        )
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logger.error("Failed to get message count: %s", e)
        return 0
    finally:
        if conn:
            release_chat_connection(conn)


def get_all_sessions() -> List[Dict]:
    if not CHAT_POSTGRES_CONNECTION_STRING:
        return []
    _ensure_tables()
    conn = None
    try:
        conn = get_chat_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.session_id, s.title, s.created_at,
                   COUNT(m.id) AS message_count
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON m.session_id = s.session_id
            GROUP BY s.session_id, s.title, s.created_at
            ORDER BY s.created_at DESC
            """
        )
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        logger.error("Failed to get sessions: %s", e)
        return []
    finally:
        if conn:
            release_chat_connection(conn)


def delete_session(session_id: str) -> None:
    if not CHAT_POSTGRES_CONNECTION_STRING:
        return
    _ensure_tables()
    conn = None
    try:
        conn = get_chat_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_messages WHERE session_id = %s", (session_id,))
        cursor.execute("DELETE FROM chat_sessions WHERE session_id = %s", (session_id,))
        conn.commit()
    except Exception as e:
        logger.error("Failed to delete session: %s", e)
    finally:
        if conn:
            release_chat_connection(conn)


def clear_logs() -> None:
    if not CHAT_POSTGRES_CONNECTION_STRING:
        return
    _ensure_tables()
    conn = None
    try:
        conn = get_chat_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "TRUNCATE TABLE chat_messages, chat_sessions RESTART IDENTITY CASCADE"
        )
        conn.commit()
        logger.info("Chat history cleared.")
    except Exception as e:
        logger.error("Failed to clear chat logs: %s", e)
    finally:
        if conn:
            release_chat_connection(conn)


# Legacy stubs
def log_query(
    question: str, sql_query: str, success: bool, error_message: str = None
) -> None:
    pass


def get_logs(limit: int = 100) -> List[Dict]:
    return get_all_sessions()[:limit]
