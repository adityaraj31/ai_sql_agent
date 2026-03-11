import sys
import logging
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from src.config import (
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
    NEO4J_DATABASE,
    LLM_MODEL_NAME,
    GROQ_API_KEY,
    DB_TYPE,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

_driver = None
_driver_lock = threading.Lock()


def get_neo4j_driver():
    global _driver
    with _driver_lock:
        if _driver is not None:
            return _driver

        if not NEO4J_URI:
            raise ValueError("NEO4J_URI is not set")

        logger.info(f"🚀 Connecting to Neo4j: {NEO4J_URI}")
        _driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
            database=NEO4J_DATABASE,
        )
        logger.info("✅ Neo4j connection established")
        return _driver


def close_neo4j_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None
        logger.info("✅ Neo4j connection closed")


def get_llm():
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set")
    return ChatGroq(temperature=0, model_name=LLM_MODEL_NAME, api_key=GROQ_API_KEY)


def test_connection() -> bool:
    """Test Neo4j connection."""
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            result = session.run("RETURN 1 AS num")
            record = result.single()
            logger.info(f"✅ Neo4j connection test: {record}")
        return True
    except Exception as e:
        logger.error(f"❌ Neo4j connection failed: {e}")
        return False


def clear_schema_graph():
    """Clear all nodes and relationships from the schema graph."""
    driver = get_neo4j_driver()
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        logger.info("✅ Schema graph cleared")


def build_schema_graph(
    schema: Dict[str, List[str]], foreign_keys: List[Dict[str, str]] = None
):
    """
    Build a knowledge graph from database schema.

    Creates nodes for:
    - Database (root node)
    - Tables
    - Columns

    Creates relationships for:
    - Database -> Table (HAS_TABLE)
    - Table -> Column (HAS_COLUMN)
    - Column -> Table (REFERENCES) for foreign keys
    - Table -> Table (RELATED_TO) for foreign key relationships
    """
    driver = get_neo4j_driver()

    with driver.session() as session:
        # Create Database node
        session.run("""
            MERGE (d:Database {name: 'chinook'})
            RETURN d
        """)

        # Create Table and Column nodes
        for table_name, columns in schema.items():
            # Create Table node
            session.run(
                """
                MATCH (d:Database {name: 'chinook'})
                MERGE (t:Table {name: $table_name})
                MERGE (d)-[:HAS_TABLE]->(t)
                RETURN t
            """,
                table_name=table_name,
            )

            # Create Column nodes
            for col in columns:
                col_name, col_type = parse_column(col)
                session.run(
                    """
                    MATCH (t:Table {name: $table_name})
                    MERGE (c:Column {name: $col_name, type: $col_type})
                    MERGE (t)-[:HAS_COLUMN]->(c)
                    RETURN c
                """,
                    table_name=table_name,
                    col_name=col_name,
                    col_type=col_type,
                )

        # Create foreign key relationships
        if foreign_keys:
            for fk in foreign_keys:
                source_table = fk.get("source_table")
                source_column = fk.get("source_column")
                target_table = fk.get("target_table")
                target_column = fk.get("target_column", "id")

                # Column references another table
                session.run(
                    """
                    MATCH (c:Column {name: $source_column})-[:BELONGS_TO]->(t:Table {name: $source_table})
                    MATCH (target:Table {name: $target_table})
                    MERGE (c)-[:REFERENCES]->(target)
                """,
                    source_column=source_column,
                    source_table=source_table,
                    target_table=target_table,
                )

                # Tables are related
                session.run(
                    """
                    MATCH (t1:Table {name: $source_table})
                    MATCH (t2:Table {name: $target_table})
                    MERGE (t1)-[:RELATED_TO {type: 'foreign_key'}]->(t2)
                """,
                    source_table=source_table,
                    target_table=target_table,
                )

        logger.info(f"✅ Schema graph built with {len(schema)} tables")


def parse_column(col_str: str) -> tuple:
    """Parse column string like 'id (INTEGER)' into name and type."""
    try:
        parts = col_str.rsplit("(", 1)
        name = parts[0].strip()
        col_type = parts[1].replace(")", "").strip() if len(parts) > 1 else "UNKNOWN"
        return name, col_type
    except:
        return col_str.strip(), "UNKNOWN"


def get_schema_as_text() -> str:
    """Retrieve schema from Neo4j as readable text."""
    driver = get_neo4j_driver()

    with driver.session() as session:
        # Get all tables with their columns
        result = session.run("""
            MATCH (d:Database)-[:HAS_TABLE]->(t:Table)
            OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)
            RETURN t.name as table, collect({name: c.name, type: c.type}) as columns
            ORDER BY t.name
        """)

        schema_lines = []
        for record in result:
            table = record["table"]
            columns = record["columns"]
            col_strs = [f"{c['name']} ({c['type']})" for c in columns if c["name"]]
            schema_lines.append(
                f"Table: {table}\nColumns:\n" + "\n".join([f"- {c}" for c in col_strs])
            )

        return "\n\n".join(schema_lines)


def retrieve_schema_context(user_query: str, top_k: int = 5) -> str:
    """
    Retrieve relevant schema context based on user query using graph traversal.

    Uses LLM to identify relevant tables, then retrieves them from graph.
    """
    # First, use LLM to identify which tables might be relevant
    llm = get_llm()

    schema_summary = _get_table_summary()

    prompt = PromptTemplate.from_template("""
    Given the user question: "{question}"
    
    Available tables:
    {tables}
    
    Return ONLY the table names that are relevant to answer this question, separated by commas.
    If unsure, include all tables that could be relevant.
    """)

    chain = prompt | llm
    response = chain.invoke({"question": user_query, "tables": schema_summary})

    relevant_tables = [t.strip() for t in response.content.split(",")]
    logger.info(f"🎯 Identified relevant tables: {relevant_tables}")

    # Retrieve detailed schema for those tables
    return get_schema_for_tables(relevant_tables)


def _get_table_summary() -> str:
    """Get a summary of all tables (just names)."""
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (t:Table)
            RETURN collect(t.name) as tables
        """)
        record = result.single()
        return ", ".join(record["tables"]) if record else ""


def get_schema_for_tables(table_names: List[str]) -> str:
    """Get detailed schema for specific tables."""
    if not table_names:
        return get_schema_as_text()

    driver = get_neo4j_driver()

    with driver.session() as session:
        result = session.run(
            """
            MATCH (t:Table)-[:HAS_COLUMN]->(c:Column)
            WHERE t.name IN $table_names
            RETURN t.name as table, collect({name: c.name, type: c.type}) as columns
            ORDER BY t.name
        """,
            table_names=table_names,
        )

        schema_lines = []
        for record in result:
            table = record["table"]
            columns = record["columns"]
            col_strs = [f"{c['name']} ({c['type']})" for c in columns if c["name"]]
            schema_lines.append(
                f"Table: {table}\nColumns:\n" + "\n".join([f"- {c}" for c in col_strs])
            )

        if not schema_lines:
            logger.warning(f"No tables found: {table_names}")
            return get_schema_as_text()

        # Also get related tables via foreign keys
        related_result = session.run(
            """
            MATCH (t1:Table)-[r:RELATED_TO]->(t2:Table)
            WHERE t1.name IN $table_names
            RETURN t1.name as source, t2.name as target, r.type as rel_type
        """,
            table_names=table_names,
        )

        relationships = []
        for record in related_result:
            relationships.append(
                f"- {record['source']} --[{record['rel_type']}]--> {record['target']}"
            )

        if relationships:
            schema_lines.append("\nRelationships:\n" + "\n".join(relationships))

        return "\n\n".join(schema_lines)


def get_foreign_keys_from_schema(schema: Dict[str, List[str]]) -> List[Dict[str, str]]:
    """
    Extract foreign key relationships from schema.

    Looks for common foreign key patterns in column names:
    - column_name_id -> references id in another table
    - column_name -> references primary key

    This is a heuristic approach. For more accurate FK detection,
    you can query the database metadata directly.
    """
    foreign_keys = []

    # Common foreign key patterns
    fk_patterns = [
        ("customers", "customer_id", "customerid"),
        ("employees", "employee_id", "employeeid"),
        ("invoices", "invoice_id", "invoiceid"),
        ("invoice_items", "invoice_id", "invoiceid"),
        ("tracks", "track_id", "trackid"),
        ("genres", "genre_id", "genreid"),
        ("media_types", "media_type_id", "mediatypeid"),
        ("playlists", "playlist_id", "playlistid"),
        ("playlist_track", "playlist_id", "playlistid"),
        ("playlist_track", "track_id", "trackid"),
        ("artists", "artist_id", "artistid"),
        ("albums", "album_id", "albumid"),
    ]

    for source_table, source_col, target_table in fk_patterns:
        if source_table in schema:
            # Check if the column exists in the source table
            for col in schema[source_table]:
                col_name, _ = parse_column(col)
                if col_name.lower() == source_col.lower():
                    foreign_keys.append(
                        {
                            "source_table": source_table,
                            "source_column": col_name,
                            "target_table": target_table,
                            "target_column": "id",
                        }
                    )
                    break

    return foreign_keys


if __name__ == "__main__":
    # Test connection
    if test_connection():
        logger.info("✅ Neo4j is connected and ready")
    else:
        logger.error("❌ Failed to connect to Neo4j")
