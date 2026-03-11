import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logger = logging.getLogger(__name__)
from src.config import (
    LANGCHAIN_TRACING_V2,
    LANGCHAIN_API_KEY,
    LANGCHAIN_PROJECT,
    LANGCHAIN_ENDPOINT,
)
from src.database import get_db_schema
from src.graphrag import (
    build_schema_graph,
    get_foreign_keys_from_schema,
    test_connection,
    clear_schema_graph,
)


# Initialize LangSmith Tracing
import os

if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
    logger.info("✅ LangSmith tracing enabled for ingestion")
else:
    logger.info("ℹ️  LangSmith tracing disabled")


def build_schema_graph_neo4j():
    """Build the schema graph in Neo4j from database schema."""

    # Test Neo4j connection first
    logger.info("Testing Neo4j connection...")
    if not test_connection():
        raise RuntimeError("Failed to connect to Neo4j. Please check your credentials.")

    # Clear existing graph
    logger.info("Clearing existing schema graph...")
    clear_schema_graph()

    # Get schema from database
    logger.info("Extracting schema from database...")
    schema = get_db_schema()
    logger.info(f"Found {len(schema)} tables in database")

    # Get foreign keys
    logger.info("Extracting foreign key relationships...")
    foreign_keys = get_foreign_keys_from_schema(schema)
    logger.info(f"Found {len(foreign_keys)} foreign key relationships")

    # Build graph
    logger.info("Building schema graph in Neo4j...")
    build_schema_graph(schema, foreign_keys)

    logger.info("✅ Schema graph built successfully in Neo4j!")


if __name__ == "__main__":
    build_schema_graph_neo4j()
