"""
graph_builder.py
Neo4j knowledge-graph builder for the SaaS Analytics database.

Schema (Supabase / PostgreSQL - public schema)
──────────────────────────────────────────────
users         : id, full_name, email, location
plans         : id, name, price_monthly, features
subscriptions : id, user_id → users.id, plan_id → plans.id, status, start_date
payments      : id, subscription_id → subscriptions.id, amount, status, payment_date

Key design decision
───────────────────
Foreign keys are discovered at runtime by querying PostgreSQL's
information_schema — no hardcoded column-name patterns, no guesswork.
The graph is always in sync with the real database structure.
"""

import logging
import threading
from typing import Optional

import psycopg2
from neo4j import GraphDatabase, Driver
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from src.config import (
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
    NEO4J_DATABASE,
    LLM_MODEL_NAME,
    GROQ_API_KEY,
    SUPABASE_DB_URL,  # e.g. postgresql://user:pass@host:5432/postgres
)

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DB_LABEL  = "saas_analytics"   # label used for the root Database node
PG_SCHEMA = "public"           # PostgreSQL schema to introspect

# ─────────────────────────────────────────────────────────────────────────────
# Neo4j driver  (singleton, thread-safe)
# ─────────────────────────────────────────────────────────────────────────────
_driver: Optional[Driver] = None
_driver_lock = threading.Lock()


def get_driver() -> Driver:
    global _driver
    with _driver_lock:
        if _driver is not None:
            return _driver
        if not NEO4J_URI:
            raise ValueError("NEO4J_URI is not configured.")
        logger.info("Connecting to Neo4j at %s", NEO4J_URI)
        _driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
            database=NEO4J_DATABASE,
        )
        logger.info("Neo4j connection established.")
        return _driver


def close_driver() -> None:
    global _driver
    with _driver_lock:
        if _driver:
            _driver.close()
            _driver = None
            logger.info("Neo4j connection closed.")


def test_neo4j_connection() -> bool:
    try:
        with get_driver().session() as session:
            session.run("RETURN 1")
        logger.info("Neo4j connection test passed.")
        return True
    except Exception as exc:
        logger.error("Neo4j connection test failed: %s", exc)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# PostgreSQL introspection  ← replaces all heuristic FK detection
# ─────────────────────────────────────────────────────────────────────────────
def _pg_connect():
    """Open a psycopg2 connection to Supabase / PostgreSQL."""
    if not SUPABASE_DB_URL:
        raise ValueError("SUPABASE_DB_URL is not configured.")
    return psycopg2.connect(SUPABASE_DB_URL)


def fetch_schema_from_db() -> dict[str, list[str]]:
    """
    Read every table and column from information_schema.columns.

    Returns
    -------
    { table_name: ["col_name (DATA_TYPE)", ...] }
    """
    sql = """
        SELECT table_name, column_name, data_type
        FROM   information_schema.columns
        WHERE  table_schema = %s
        ORDER  BY table_name, ordinal_position
    """
    schema: dict[str, list[str]] = {}
    with _pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (PG_SCHEMA,))
            for table, column, dtype in cur.fetchall():
                schema.setdefault(table, []).append(
                    f"{column} ({dtype.upper()})"
                )

    logger.info("Fetched schema: %d tables.", len(schema))
    return schema


def fetch_foreign_keys_from_db() -> list[dict[str, str]]:
    """
    Read every FK relationship directly from pg_catalog.

    information_schema joins are unreliable on Supabase (permission/view
    resolution issues). pg_catalog is the authoritative source and always
    returns the correct constraints.

    Returns
    -------
    [{ source_table, source_column, target_table, target_column }, ...]
    """
    sql = """
        SELECT
            src_tbl.relname  AS source_table,
            src_col.attname  AS source_column,
            tgt_tbl.relname  AS target_table,
            tgt_col.attname  AS target_column
        FROM pg_constraint c
        JOIN pg_class     src_tbl ON src_tbl.oid = c.conrelid
        JOIN pg_class     tgt_tbl ON tgt_tbl.oid = c.confrelid
        JOIN pg_attribute src_col ON src_col.attrelid = c.conrelid
                                 AND src_col.attnum = ANY(c.conkey)
        JOIN pg_attribute tgt_col ON tgt_col.attrelid = c.confrelid
                                 AND tgt_col.attnum = ANY(c.confkey)
        JOIN pg_namespace ns      ON ns.oid = src_tbl.relnamespace
        WHERE c.contype = 'f'
          AND ns.nspname = %s
        ORDER BY source_table, source_column
    """
    foreign_keys: list[dict[str, str]] = []
    with _pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (PG_SCHEMA,))
            for src_table, src_col, tgt_table, tgt_col in cur.fetchall():
                foreign_keys.append(
                    {
                        "source_table":  src_table,
                        "source_column": src_col,
                        "target_table":  tgt_table,
                        "target_column": tgt_col,
                    }
                )

    logger.info("Fetched %d foreign key(s).", len(foreign_keys))
    return foreign_keys


# ─────────────────────────────────────────────────────────────────────────────
# Graph construction
# ─────────────────────────────────────────────────────────────────────────────
def clear_graph() -> None:
    with get_driver().session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    logger.info("Graph cleared.")


def _parse_column(col_str: str) -> tuple[str, str]:
    """'col_name (TYPE)' → ('col_name', 'TYPE')"""
    parts    = col_str.rsplit("(", 1)
    name     = parts[0].strip()
    col_type = parts[1].rstrip(")").strip() if len(parts) > 1 else "UNKNOWN"
    return name, col_type


def build_graph(
    schema: dict[str, list[str]],
    foreign_keys: list[dict[str, str]],
    db_label: str = DB_LABEL,
) -> None:
    """
    Load schema + FKs into Neo4j.

    Nodes         : Database  Table  Column
    Relationships : HAS_TABLE  HAS_COLUMN  FK_TO  RELATED_TO
    """
    with get_driver().session() as session:

        # Root node
        session.run("MERGE (d:Database {name: $name})", name=db_label)

        # Tables and columns
        for table, columns in schema.items():
            session.run(
                """
                MATCH (d:Database {name: $db})
                MERGE (t:Table {name: $table})
                MERGE (d)-[:HAS_TABLE]->(t)
                """,
                db=db_label, table=table,
            )
            for col_str in columns:
                col_name, col_type = _parse_column(col_str)
                session.run(
                    """
                    MATCH (t:Table {name: $table})
                    MERGE (c:Column {name: $col, table: $table})
                    SET   c.type = $col_type
                    MERGE (t)-[:HAS_COLUMN]->(c)
                    """,
                    table=table, col=col_name, col_type=col_type,
                )

        # Foreign keys  (sourced directly from PostgreSQL — always accurate)
        for fk in foreign_keys:
            # Column-level edge
            session.run(
                """
                MATCH (src:Column {name: $src_col, table: $src_table})
                MATCH (tgt:Column {name: $tgt_col, table: $tgt_table})
                MERGE (src)-[:FK_TO]->(tgt)
                """,
                src_col=fk["source_column"], src_table=fk["source_table"],
                tgt_col=fk["target_column"], tgt_table=fk["target_table"],
            )
            # Table-level shortcut (handy for graph traversal queries)
            session.run(
                """
                MATCH (t1:Table {name: $src})
                MATCH (t2:Table {name: $tgt})
                MERGE (t1)-[:RELATED_TO {via: $col}]->(t2)
                """,
                src=fk["source_table"],
                tgt=fk["target_table"],
                col=fk["source_column"],
            )

    logger.info("Graph built: %d tables, %d FK(s).", len(schema), len(foreign_keys))


# ─────────────────────────────────────────────────────────────────────────────
# Schema retrieval (reads from Neo4j)
# ─────────────────────────────────────────────────────────────────────────────
def get_full_schema_text() -> str:
    """Human-readable dump of every table and column."""
    with get_driver().session() as session:
        result = session.run(
            """
            MATCH (t:Table)-[:HAS_COLUMN]->(c:Column)
            RETURN t.name AS table,
                   collect({name: c.name, type: c.type}) AS columns
            ORDER BY t.name
            """
        )
        lines = []
        for record in result:
            cols = ", ".join(
                f"{c['name']} ({c['type']})"
                for c in record["columns"] if c["name"]
            )
            lines.append(f"Table {record['table']}: {cols}")
    return "\n".join(lines)


def get_schema_for_tables(table_names: list[str]) -> str:
    """
    Return schema text for *table_names* plus their FK-connected neighbours.
    Falls back to the full schema when *table_names* is empty.
    """
    if not table_names:
        return get_full_schema_text()

    with get_driver().session() as session:
        result = session.run(
            """
            MATCH (t:Table)-[:HAS_COLUMN]->(c:Column)
            WHERE t.name IN $names
            RETURN t.name AS table,
                   collect({name: c.name, type: c.type}) AS columns
            ORDER BY t.name
            """,
            names=table_names,
        )
        lines = []
        for record in result:
            cols = ", ".join(
                f"{c['name']} ({c['type']})"
                for c in record["columns"] if c["name"]
            )
            lines.append(f"Table {record['table']}: {cols}")

        if not lines:
            logger.warning("No tables matched %s — returning full schema.", table_names)
            return get_full_schema_text()

        rels = session.run(
            """
            MATCH (t1:Table)-[r:RELATED_TO]->(t2:Table)
            WHERE t1.name IN $names
            RETURN t1.name AS src, r.via AS via, t2.name AS tgt
            """,
            names=table_names,
        )
        fk_lines = [f"  {r['src']}.{r['via']} → {r['tgt']}" for r in rels]
        if fk_lines:
            lines.append("\nForeign keys:\n" + "\n".join(fk_lines))

    return "\n".join(lines)


def _get_all_table_names() -> list[str]:
    with get_driver().session() as session:
        record = session.run(
            "MATCH (t:Table) RETURN collect(t.name) AS names"
        ).single()
        return record["names"] if record else []


# ─────────────────────────────────────────────────────────────────────────────
# LLM-powered context retrieval
# ─────────────────────────────────────────────────────────────────────────────
def get_llm() -> ChatGroq:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured.")
    return ChatGroq(temperature=0, model=LLM_MODEL_NAME, api_key=GROQ_API_KEY)


def retrieve_schema_context(user_query: str) -> str:
    """
    Ask the LLM which tables are relevant to *user_query*, then return
    their schema + FK relationships from the graph.
    """
    all_tables = _get_all_table_names()
    if not all_tables:
        logger.warning("Graph is empty — rebuild with initialise_graph().")
        return ""

    prompt = PromptTemplate.from_template(
        "You are a SQL expert. Given the question below, return ONLY the "
        "comma-separated table names needed to answer it — no other text.\n\n"
        "Available tables: {tables}\n\n"
        "Question: {question}"
    )
    response = (prompt | get_llm()).invoke(
        {"question": user_query, "tables": ", ".join(all_tables)}
    )
    relevant = [t.strip() for t in response.content.split(",") if t.strip()]
    logger.info("Relevant tables: %s", relevant)
    return get_schema_for_tables(relevant)


# ─────────────────────────────────────────────────────────────────────────────
# One-shot initialisation
# ─────────────────────────────────────────────────────────────────────────────
def initialise_graph(clear_first: bool = True) -> None:
    """
    Pull the live schema and FK constraints from PostgreSQL, then load
    them into Neo4j.  Call this once on application startup.
    """
    if clear_first:
        clear_graph()
    schema       = fetch_schema_from_db()
    foreign_keys = fetch_foreign_keys_from_db()
    build_graph(schema, foreign_keys)
    logger.info("SaaS Analytics graph is ready.")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not test_neo4j_connection():
        raise SystemExit("Cannot connect to Neo4j — check your configuration.")
    initialise_graph()
    print(get_full_schema_text())