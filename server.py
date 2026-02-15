from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
import sys
import os

# Add src to path for imports
sys.path.insert(0, ".")

# Initialize LangSmith Tracing
from src.config import (
    LANGCHAIN_TRACING_V2, 
    LANGCHAIN_API_KEY, 
    LANGCHAIN_PROJECT,
    LANGCHAIN_ENDPOINT
)

if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
    print("✅ LangSmith tracing enabled")
else:
    print("ℹ️  LangSmith tracing disabled (set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in .env to enable)")

from src.rag import generate_sql
from src.database import run_sql_query
from src.logger import log_query, get_logs, clear_logs

app = FastAPI(
    title="AI SQL Agent API",
    description="FastAPI backend for AI SQL Agent",
    version="1.0.0"
)

# --- Pydantic Models ---

class ChatMessage(BaseModel):
    role: str
    content: str
    sql: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None

class ChatRequest(BaseModel):
    question: str
    chat_history: List[ChatMessage] = []

class ChatResponse(BaseModel):
    success: bool
    sql_query: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    message: str

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
    return {
        "status": "ok",
        "service": "AI SQL Agent API",
        "version": "1.0.0"
    }

@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a user question and return generated SQL and results.
    
    Args:
        request: ChatRequest with question and optional chat_history
        
    Returns:
        ChatResponse with SQL query and execution results
    """
    question = request.question
    chat_history = request.chat_history
    
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        # Convert Pydantic models back to dicts for rag.generate_sql
        history_dicts = [msg.dict() for msg in chat_history]
        
        # Generate SQL
        sql_query = generate_sql(question, history_dicts)
        
        if not sql_query:
            return ChatResponse(
                success=False,
                error="Failed to generate SQL query",
                message="The AI agent could not generate a valid SQL query"
            )
        
        # Execute SQL
        results, error = run_sql_query(sql_query)
        
        # Log the query
        if error:
            log_query(question, sql_query, success=False, error_message=error)
        else:
            log_query(question, sql_query, success=True)
        
        # Prepare response
        if error:
            return ChatResponse(
                success=False,
                sql_query=sql_query,
                error=error,
                message=f"Error executing query: {error}"
            )
        else:
            return ChatResponse(
                success=True,
                sql_query=sql_query,
                results=results,
                message="Query executed successfully"
            )
            
    except Exception as e:
        # Log unexpected errors
        log_query(question, "", success=False, error_message=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/history")
async def get_history() -> Dict[str, Any]:
    """
    Retrieve query history logs.
    
    Returns:
        Dict containing list of query logs and count
    """
    try:
        logs = get_logs()
        return {
            "success": True,
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")

@app.delete("/history")
async def clear_history() -> Dict[str, Any]:
    """
    Clear all query history logs.
    
    Returns:
        Dict containing success status
    """
    try:
        clear_logs()
        return {
            "success": True,
            "message": "Query history cleared successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(e)}")

# --- Main ---

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
