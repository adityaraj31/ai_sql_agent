from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import uvicorn
import sys
import os
import re
import threading
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize LangSmith Tracing
# LangSmith tracing is disabled
# from src.config import (
#     LANGCHAIN_TRACING_V2,
#     LANGCHAIN_API_KEY,
#     LANGCHAIN_PROJECT,
#     LANGCHAIN_ENDPOINT,
# )

# if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
#     os.environ["LANGCHAIN_TRACING_V2"] = "true"
#     os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
#     os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
#     os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
#     logger.info("✅ LangSmith tracing enabled")
# else:
#     logger.info(
#         "ℹ️  LangSmith tracing disabled (set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in .env to enable)"
#     )

from src.config import ALLOWED_ORIGINS

from src.rag import generate_sql, check_question_relevance
from src.database import run_sql_query
from src.logger import (
    create_session,
    add_message,
    get_all_sessions,
    get_session_messages,
    delete_session,
    clear_logs,
)
from src.ingestion import build_schema_graph_neo4j

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown handlers."""
    from src.graphrag import test_neo4j_connection, close_driver
    from src.database import close_all_pools
    from src.logger import close_chat_pool

    logger.info("Starting AI SQL Agent...")

    neo4j_ok = test_neo4j_connection()
    if neo4j_ok:
        logger.info("✅ Neo4j connection verified")
    else:
        logger.warning("⚠️ Neo4j not available - GraphRAG features disabled")

    yield

    logger.info("Shutting down AI SQL Agent...")
    close_all_pools()
    close_chat_pool()
    close_driver()
    logger.info("Connection pools closed")


app = FastAPI(
    title="AI SQL Agent API",
    description="FastAPI backend for AI SQL Agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Input Validation Constants ---
MAX_QUESTION_LENGTH = 1000
MAX_SESSION_ID_LENGTH = 100
MAX_HISTORY_MESSAGES = 50

# --- Rate Limiting Constants ---
RATE_LIMIT_REQUESTS = 30  # Max requests
RATE_LIMIT_WINDOW = 60  # Per window (seconds)


class RateLimiter:
    """Simple in-memory rate limiter using sliding window."""

    def __init__(
        self,
        max_requests: int = RATE_LIMIT_REQUESTS,
        window_seconds: int = RATE_LIMIT_WINDOW,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed for given identifier."""
        with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.window_seconds)

            # Clean old requests
            self.requests[identifier] = [
                ts for ts in self.requests[identifier] if ts > cutoff
            ]

            # Check limit
            if len(self.requests[identifier]) >= self.max_requests:
                return False

            # Add current request
            self.requests[identifier].append(now)
            return True

    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests for identifier."""
        with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.window_seconds)

            self.requests[identifier] = [
                ts for ts in self.requests[identifier] if ts > cutoff
            ]

            return max(0, self.max_requests - len(self.requests[identifier]))


# Global rate limiter instance
rate_limiter = RateLimiter()


# --- Input Sanitization ---
def sanitize_input(text: str, max_length: int) -> str:
    """Sanitize and validate input text."""
    if not text:
        return ""
    # Remove null bytes and control characters (except newlines/tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Trim whitespace
    text = text.strip()
    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length]
    return text


def validate_session_id(session_id: str) -> str:
    """Validate and sanitize session ID."""
    if not session_id:
        return session_id
    # Only allow alphanumeric, underscores, hyphens
    session_id = re.sub(r"[^a-zA-Z0-9_-]", "", session_id)
    if len(session_id) > MAX_SESSION_ID_LENGTH:
        session_id = session_id[:MAX_SESSION_ID_LENGTH]
    return session_id


# --- Pydantic Models ---


class ChatMessage(BaseModel):
    role: str
    content: str
    sql: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    chat_history: List[ChatMessage] = []

    @field_validator("question")
    @classmethod
    def validate_question(cls, v):
        if not v or not v.strip():
            raise ValueError("Question cannot be empty")
        if len(v) > MAX_QUESTION_LENGTH:
            raise ValueError(f"Question cannot exceed {MAX_QUESTION_LENGTH} characters")
        return v

    @field_validator("chat_history")
    @classmethod
    def validate_history(cls, v):
        if len(v) > MAX_HISTORY_MESSAGES:
            raise ValueError(
                f"Chat history cannot exceed {MAX_HISTORY_MESSAGES} messages"
            )
        return v


class ChatResponse(BaseModel):
    success: bool
    sql_query: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    message: str
    is_relevant: Optional[bool] = True


class QueryLog(BaseModel):
    timestamp: str
    question: str
    sql_query: str
    success: bool
    error_message: Optional[str] = None


# --- Endpoints ---


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "AI SQL Agent API", "version": "1.0.0"}


@app.post("/chat")
async def chat(http_request: Request, request: ChatRequest) -> ChatResponse:
    """
    Process a user question and return generated SQL and results.

    Args:
        http_request: FastAPI request object (for rate limiting)
        request: ChatRequest with question and optional chat_history

    Returns:
        ChatResponse with SQL query and execution results
    """
    # Rate limiting - use IP + session as identifier
    client_ip = http_request.client.host if http_request.client else "unknown"
    identifier = f"{client_ip}:{request.session_id or 'default'}"

    if not rate_limiter.is_allowed(identifier):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds.",
        )
    # Sanitize inputs (Pydantic already validated length)
    question = sanitize_input(request.question, MAX_QUESTION_LENGTH)
    session_id = validate_session_id(
        request.session_id or f"session_{int(datetime.now().timestamp())}"
    )
    chat_history = request.chat_history

    try:
        # Create session if not exists
        create_session(session_id)

        # Store user message (sanitize content from history too)
        add_message(session_id, role="user", content=question)

        # Convert Pydantic models to dicts, excluding large 'results' field to avoid confusing the LLM
        history_dicts = []
        for msg in chat_history:
            msg_dict = {
                "role": sanitize_input(msg.role, 50),
                "content": sanitize_input(msg.content, MAX_QUESTION_LENGTH),
            }
            if msg.sql:
                msg_dict["sql"] = sanitize_input(msg.sql, 2000)
            history_dicts.append(msg_dict)

        # Check if question is relevant to the database schema
        from src.graphrag import get_full_schema_text, _get_all_table_names

        schema_text = get_full_schema_text()
        is_relevant, _ = check_question_relevance(question, schema_text)

        if not is_relevant:
            # Question is irrelevant - return a helpful redirect message
            table_names = _get_all_table_names()

            if table_names:
                redirect_msg = f"I'd love to help with that, but I'm currently set up to only answer questions about your database records. Feel free to ask me something about {', '.join(table_names[:5])} instead!"
            else:
                redirect_msg = "I'd love to help with that, but I'm currently set up to only answer questions about your database records. Feel free to ask me about your data!"

            add_message(session_id, role="assistant", content=redirect_msg)

            return ChatResponse(
                success=True,
                message=redirect_msg,
                is_relevant=False,
            )

        # Generate SQL
        sql_query = generate_sql(question, history_dicts)

        if not sql_query:
            add_message(
                session_id, role="assistant", content="Failed to generate SQL query"
            )
            return ChatResponse(
                success=False,
                error="Failed to generate SQL query",
                message="The AI agent could not generate a valid SQL query",
            )

        # Execute SQL
        results, error = run_sql_query(sql_query)

        # Check if question is irrelevant (LLM returned service message)
        is_relevant = True
        if sql_query and "Service_Message" in sql_query:
            is_relevant = False
            results = None
            response_content = "This question is outside the scope of the database. I can only answer questions about the connected database."
        else:
            response_content = f"Query executed successfully. Results: {len(results) if results else 0} rows."

        # Store assistant response
        add_message(
            session_id,
            role="assistant",
            content=response_content,
            sql_query=sql_query,
            results=results or [],
        )

        # Prepare response
        if error:
            return ChatResponse(
                success=False,
                sql_query=sql_query,
                error=error,
                message=f"Error executing query: {error}",
                is_relevant=is_relevant,
            )
        else:
            return ChatResponse(
                success=True,
                sql_query=sql_query,
                results=results,
                message="Query executed successfully",
                is_relevant=is_relevant,
            )

    except Exception as e:
        # Log unexpected errors
        add_message(session_id, role="assistant", content=f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/embeddings")
async def create_embeddings(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Trigger the creation of schema graph in Neo4j in the background.
    """
    try:
        # Mark embedding as in progress
        import json

        with open("embedding_status.json", "w") as f:
            json.dump(
                {"status": "in_progress", "message": "Building schema graph..."}, f
            )

        # Run the long-running task in the background
        background_tasks.add_task(build_schema_graph_neo4j)
        return {
            "success": True,
            "message": "Schema graph build started in the background (this may take 1-2 minutes)",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start schema graph build: {str(e)}"
        )


@app.get("/embeddings/status")
async def get_embeddings_status() -> Dict[str, Any]:
    """
    Check the status of embedding creation.
    """
    try:
        import json
        from pathlib import Path

        status_file = Path("embedding_status.json")
        if status_file.exists():
            with open(status_file, "r") as f:
                return json.load(f)
        return {"status": "not_started", "message": "No embedding process started yet"}
    except Exception as e:
        return {"status": "unknown", "message": str(e)}


@app.get("/history")
async def get_history() -> Dict[str, Any]:
    """
    Retrieve chat history sessions.

    Returns:
        Dict containing list of chat sessions and count
    """
    try:
        sessions = get_all_sessions()
        return {"success": True, "count": len(sessions), "logs": sessions}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve history: {str(e)}"
        )


@app.get("/history/{session_id}")
async def get_session_history(session_id: str) -> Dict[str, Any]:
    """
    Retrieve messages for a specific session.

    Returns:
        Dict containing list of messages for the session
    """
    try:
        messages = get_session_messages(session_id)
        return {"success": True, "session_id": session_id, "messages": messages}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve session: {str(e)}"
        )


@app.delete("/history/{session_id}")
async def delete_session_history(session_id: str) -> Dict[str, Any]:
    """
    Delete a specific session.
    """
    try:
        delete_session(session_id)
        return {"success": True, "message": "Session deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete session: {str(e)}"
        )


@app.delete("/history")
async def clear_history() -> Dict[str, Any]:
    """
    Clear all query history logs.

    Returns:
        Dict containing success status
    """
    try:
        clear_logs()
        return {"success": True, "message": "Query history cleared successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to clear history: {str(e)}"
        )


# --- Main ---

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
