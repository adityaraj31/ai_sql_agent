import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logger = logging.getLogger(__name__)

# LangSmith tracing is disabled
# from src.config import (
#     LANGCHAIN_TRACING_V2,
#     LANGCHAIN_API_KEY,
#     LANGCHAIN_PROJECT,
#     LANGCHAIN_ENDPOINT,
# )

from src.database import get_db_schema
from src.graphrag import (
    build_graph,
    fetch_foreign_keys_from_db,
    test_neo4j_connection,
    clear_graph,
)


# LangSmith tracing is disabled
# import os
# if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
#     os.environ["LANGCHAIN_TRACING_V2"] = "true"
#     os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
#     os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
#     os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
#     logger.info("✅ LangSmith tracing enabled for ingestion")
# else:
#     logger.info("ℹ️  LangSmith tracing disabled")


def build_schema_graph_neo4j():
    """Build the schema graph in Neo4j from database schema."""

    # Test Neo4j connection first
    logger.info("Testing Neo4j connection...")
    if not test_neo4j_connection():
        raise RuntimeError("Failed to connect to Neo4j. Please check your credentials.")

    # Clear existing graph
    logger.info("Clearing existing schema graph...")
    clear_graph()

    # Get schema from database
    logger.info("Extracting schema from database...")
    schema = get_db_schema()
    logger.info(f"Found {len(schema)} tables in database")

    # Get foreign keys
    logger.info("Extracting foreign key relationships...")
    foreign_keys = fetch_foreign_keys_from_db()
    logger.info(f"Found {len(foreign_keys)} foreign key relationships")

    # Build graph
    logger.info("Building schema graph in Neo4j...")
    build_graph(schema, foreign_keys)

    logger.info("✅ Schema graph built successfully in Neo4j!")

    # Update status file
    try:
        import json

        with open("embedding_status.json", "w") as f:
            json.dump(
                {"status": "completed", "message": "Schema graph built successfully!"},
                f,
            )
    except Exception:
        logger.warning("Failed to update embedding status file")


if __name__ == "__main__":
    build_schema_graph_neo4j()
