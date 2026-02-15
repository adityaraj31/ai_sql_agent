# 🧠 AI SQL Agent

A GenAI-powered intelligent SQL assistant that converts natural language questions into executable SQL queries, provides autonomous visualizations, and maintains conversational context.

> **Built using:** LangChain + Pinecone + Groq + Streamlit  
> **Backend:** Python + SQLite (Chinook DB)

---

## 🚀 Problem Statement

Non-technical stakeholders (like managers, marketers, and analysts) often struggle to retrieve insights from raw databases because they don't know SQL.

### 🔍 Example Problems:

> "Show me the top five customers by total invoice value"  
> "How many orders did we receive from each country?"  
> "Show total sales grouped by country"

Manually writing SQL queries for such questions is slow, repetitive, and requires technical knowledge.

---

## ✅ Use Case

This tool bridges the gap between business users and SQL databases by allowing anyone to ask data questions in plain English.

### 💼 Ideal For:

- Business dashboards
- Internal analytics tools
- Data teams working with non-technical users
- Students and developers building RAG-based AI apps

---

## 🛠 Tech Stack

| Component     | Tool / Framework                                       |
| ------------- | ------------------------------------------------------ |
| LLM           | [Groq](https://groq.com/) (Llama3.3 70B Turbo)         |
| RAG Framework | [LangChain](https://www.langchain.com/)                |
| Vector DB     | [Pinecone](https://www.pinecone.io/) (Cloud Vector DB) |
| Tracing       | [LangSmith](https://smith.langchain.com/)              |
| Frontend      | [Streamlit](https://streamlit.io/)                     |
| Database      | Chinook SQLite (sample DB)                             |

---

## 🧩 Folder Structure

```
ai-sql-agent/
├── data/
│   └── chinook.db              # SQLite database
├── src/
│   ├── ingestion.py            # Vector store creation/doc embedding
│   ├── rag.py                  # Core RAG logic & SQL generation
│   ├── database.py             # Database operations & safety checks
│   ├── logger.py               # Query logging
│   ├── visualization.py        # Dynamic chart generation
│   └── config.py               # Configuration constants
├── app.py                      # Main Streamlit application
├── server.py                   # FastAPI backend
├── requirements.txt            # Project dependencies
└── .env                        # API Keys (Groq, Pinecone, LangSmith)
```

---

## 🔍 LangSmith Tracing & Monitoring

Full observability is integrated via **LangSmith** to monitor LLM latency, token usage, and RAG retrieval accuracy.

### ✨ Highlights:
- **Trace Visibility**: Inspect every step of the reformulation and generation chain.
- **Performance Metrics**: Monitor token usage and latency for Llama3.3.
- **Error Tracking**: Identify schema retrieval gaps or SQL syntax errors instantly.

---

## ▶️ How to Run Locally

1. **Clone the repo**
   ```bash
   git clone https://github.com/adityaraj31/ai-sql-agent.git
   cd ai-sql-agent
   ```

2. **Install Dependencies** (Recommended: [uv](https://github.com/astral-sh/uv))
   ```bash
   uv pip install -r requirements.txt
   ```

3. **Set Environment Variables**
   Create a `.env` file:
   ```env
   GROQ_API_KEY=your_groq_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_INDEX_NAME=your_index_name
   
   # Tracing (Optional)
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_langsmith_api_key
   LANGCHAIN_PROJECT=ai-sql-agent
   ```

4. **Initialize Data**
   ```bash
   python src/ingestion.py
   ```

5. **Start Backend & App**
   Run the FastAPI server and Streamlit app:
   ```bash
   # Terminal 1
   python server.py
   
   # Terminal 2
   streamlit run app.py
   ```

---

## 🙋‍♂️ Author

**Aditya Raj Singh**  
📍 GenAI & MERN Stack Developer  
🔗 [LinkedIn](https://linkedin.com/in/adityaraj31)  
🚀 Deep Learning | Multi-Agent Systems | RAG Pipelines

---

## ⭐️ Support the Project
If you find this project useful, please give it a ⭐️ on GitHub and connect with me for collaborations!
