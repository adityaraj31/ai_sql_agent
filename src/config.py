import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base Directory
BASE_DIR = Path(__file__).parent.parent

# Database Configuration
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()  # Default to SQLite

# SQLite Configuration
DB_PATH = BASE_DIR / "data" / "chinook.db"

# PostgreSQL Configuration
POSTGRES_CONNECTION_STRING = os.getenv("POSTGRES_CONNECTION_STRING", "")
SUPABASE_DB_URL = os.getenv(
    "SUPABASE_DB_URL", os.getenv("POSTGRES_CONNECTION_STRING", "")
)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", "ai_sql_db")

# Chat History PostgreSQL Configuration
CHAT_POSTGRES_CONNECTION_STRING = os.getenv("CHAT_POSTGRES_CONNECTION_STRING", "")

# Neo4j Configuration (GraphRAG)
NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Logging
# Chat history is now stored in PostgreSQL (see CHAT_POSTGRES_CONNECTION_STRING)

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# LangSmith Tracing Configuration (commented out)
# LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
# LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
# LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "ai-sql-agent")
# LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

# Models
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL_NAME = "llama-3.3-70b-versatile"

# Security
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")
