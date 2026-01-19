# 🧠 AI SQL Agent

A GenAI-powered intelligent SQL assistant that converts natural language questions into executable SQL queries and displays results from a real database.

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

| Component     | Tool / Framework            |
|---------------|-----------------------------|
| LLM           | [Groq](https://groq.com/) (Llama3 Turbo) |
| RAG Framework | [LangChain](https://www.langchain.com/) |
| Vector DB     | [Pinecone](https://www.pinecone.io/) (Cloud Vector DB) |
| Frontend      | [Streamlit](https://streamlit.io/) |
| Database      | Chinook SQLite (sample DB)  |
| Language      | Python                      |

---

## 🧩 Features

- 🔍 **Ask in Plain English**: Convert natural language to SQL.
- ⚡ **Cloud Vector Search**: Uses **Pinecone** for scalable, high-speed schema retrieval.
- 📜 **Auto-Generated SQL**: Powered by Llama3 on Groq.
- 💾 **Real Data Execution**: Runs queries securely on a local SQLite database.
- � **Query History**: View past queries, generated SQL, and execution status in the sidebar.
- � **Logging**: Automatically logs all user interactions for auditing.
- 🔐 **Secure**: Uses `.env` for API key management.

---

## 🧱 Folder Structure

```
ai-sql-agent/
├── data/
│   └── chinook.db              # SQLite database
├── tests/
│   ├── test_integration.py     # Complex query integration tests
│   └── test_edge_cases.py      # Safety & edge case tests
├── src/
│   ├── ingestion.py            # Vector store creation/doc embedding
│   ├── rag.py                  # Core RAG logic & SQL generation
│   ├── database.py             # Database operations & safety checks
│   ├── logger.py               # Query logging
│   ├── visualization.py        # Dynamic chart generation
│   └── config.py               # Configuration constants
├── app.py                      # Main Streamlit application
├── requirements.txt            # Project dependencies
└── .env                        # API Keys (Groq, Pinecone)
```

---

## ▶️ How to Run Locally

1. **Clone the repo**
   ```bash
   git clone https://github.com/yourusername/ai-sql-agent.git
   cd ai-sql-agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set your API keys**
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   ```

4. **Initialize Vector Store**
   Run the setup script:
   ```bash
   python src/ingestion.py
   ```

5. **Run the App**
   ```bash
   streamlit run app.py
   ```

6. **Run Tests**
   To execute the test suite (ensures complex queries are working):
   ```bash
   pytest tests/
   ```

---

## 📸 UI Preview

> ![Preview](preview_screenshot.png)

---

## 🧠 Powered By

- **LangChain** for RAG orchestration
- **Pinecone** for serverless vector storage
- **Groq** for ultra-fast LLM inference
- **Streamlit** for the interactive dashboard

---

## 🙋‍♂️ Author

**Aditya Raj Singh**  
📍 GenAI & MERN Stack Developer  
🎓 KCC Institute of Technology and Management  
🔗 [LinkedIn](https://linkedin.com/in/your-profile)

---

## 📌 Future Work

- [ ] Support for PostgreSQL / MySQL
- [x] Natural language filtering & grouping (Completed with Llama 3.3 70B ✅)
- [x] **Chart/graph visualizations** (Completed ✅)
- [x] **User query history and logs** (Completed ✅)
- [x] **SQL Safety Guardrails** (Completed ✅)
- [x] **External Vector DB Integration** (Completed ✅)

---

## ⭐️ If you liked this project

- Drop a ⭐️ on GitHub
- Connect with me on LinkedIn
- Fork and extend it!