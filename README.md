# AI SQL Agent

A GenAI-powered intelligent SQL assistant that converts natural language questions into executable SQL queries, provides autonomous visualizations, and maintains conversational context with session history.

> **Built using:** LangChain + Neo4j + Groq + React  
> **Backend:** Python + FastAPI + PostgreSQL  
> **Frontend:** React + Vite + TypeScript

---

## Problem Statement

Non-technical stakeholders (like managers, marketers, and analysts) often struggle to retrieve insights from raw databases because they don't know SQL.

### Example Problems

> "Show me top customers by total spending"  
> "How many active subscriptions do we have?"  
> "What's the monthly revenue trend?"

Manually writing SQL queries for such questions is slow, repetitive, and requires technical knowledge.

---

## Use Case

This tool bridges the gap between business users and SQL databases by allowing anyone to ask data questions in plain English.

### Ideal For

- Business dashboards
- Internal analytics tools
- Data teams working with non-technical users
- SaaS analytics with subscription data

---

## Tech Stack

| Component     | Tool / Framework                                       |
| ------------- | ------------------------------------------------------ |
| LLM           | OpenRouter (OpenAI GPT-4o-mini)                       |
| RAG Framework | LangChain                                             |
| Graph DB      | Neo4j (Knowledge Graph for Schema)                    |
| Backend       | FastAPI (Python)                                      |
| Frontend      | React + Vite + TypeScript                             |
| Database      | PostgreSQL (Supabase)                                 |
| Chat Storage  | PostgreSQL (Separate database for sessions)           |

---

## Features

- **Natural Language to SQL** - Ask questions in plain English, get SQL results
- **GraphRAG Schema Retrieval** - Neo4j-powered schema understanding
- **Session Management** - Conversations stored with LLM-generated titles
- **Chat History** - Load previous conversations from sidebar
- **Golden SQL Examples** - Few-shot learning for complex queries
- **SQL Safety** - Read-only queries only, validation before execution
- **Comparison Queries** - Year-over-year, month-over-month analysis

---

## Folder Structure

```
ai-sql-agent/
├── src/
│   ├── config.py               # Configuration & environment variables
│   ├── database.py             # Database operations & safety checks
│   ├── graphrag.py             # Neo4j GraphRAG for schema retrieval
│   ├── ingestion.py            # Schema graph building
│   ├── llm.py                  # Shared LLM singleton
│   ├── logger.py               # Chat session storage (PostgreSQL)
│   ├── rag.py                  # Core RAG logic & SQL generation
│   └── visualization.py        # Dynamic chart generation (Plotly)
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── services/           # API calls
│   │   ├── types/              # TypeScript types
│   │   ├── App.tsx             # Main application
│   │   └── App.css             # Styles
│   └── package.json
├── server.py                   # FastAPI backend
├── pyproject.toml              # Python dependencies
└── .env                       # Environment variables
```

---

## Getting Started

### Prerequisites

- Python 3.13+
- Node.js 18+
- PostgreSQL database (Supabase)
- Neo4j database

### Installation

1. **Clone the repo**
   ```bash
   cd ai-sql-agent
   ```

2. **Install Python dependencies**
   ```bash
   uv sync
   # or
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   ```

### Environment Variables

Create a `.env` file:

```env
# OpenRouter (OpenAI GPT-4o-mini)
OPENROUTER_API_KEY=your_openrouter_api_key

# Database Configuration
DB_TYPE=postgres
POSTGRES_CONNECTION_STRING=postgresql://postgres:password@host:5432/postgres

# Chat History Database
CHAT_POSTGRES_CONNECTION_STRING=postgresql://postgres:password@host:5432/postgres

# Neo4j Configuration (GraphRAG)
NEO4J_URI=neo4j+s://your-neo4j-uri
NEO4J_USERNAME=your_username
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

# Frontend CORS (optional)
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# LangSmith Tracing (commented out by default)
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=your_langsmith_api_key
# LANGCHAIN_PROJECT=ai-sql-agent
```

### Running the Application

1. **Start the backend**
   ```bash
   uv run python server.py
   ```

2. **Start the frontend** (in a new terminal)
   ```bash
   cd frontend
   npm run dev
   ```

3. **Build schema graph** (first time or to refresh)
   - Click "Create Embeddings" button in the sidebar
   - Or call the API: `POST /embeddings`

4. **Open browser**
   - Frontend: http://localhost:5173

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/chat` | Send a chat message |
| GET | `/history` | List all chat sessions |
| GET | `/history/{session_id}` | Get messages for a session |
| DELETE | `/history/{session_id}` | Delete a session |
| DELETE | `/history` | Clear all history |
| POST | `/embeddings` | Build schema graph (background) |
| GET | `/embeddings/status` | Check embedding status |

---

## Database Schema

The agent works with any PostgreSQL database. Example tables:

- `users` - User information
- `plans` - Subscription plans
- `subscriptions` - User subscriptions
- `payments` - Payment records

---

## Architecture

1. **User Question** → FastAPI endpoint
2. **Question Reformulation** → LLM converts follow-up questions to standalone
3. **Schema Retrieval** → Neo4j GraphRAG finds relevant tables/columns
4. **SQL Generation** → LLM generates SQL with Golden Examples
5. **Safety Check** → Validate read-only queries
6. **Execution** → Run SQL against PostgreSQL
7. **Storage** → Save conversation to PostgreSQL
8. **Response** → Return results to frontend

---

## License

MIT License
