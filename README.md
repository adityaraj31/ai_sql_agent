# 🧠 AI SQL Agent for Business Dashboard

A GenAI-powered intelligent SQL assistant that converts natural language questions into executable SQL queries and displays results from a real database.

> Built using LangChain + FAISS + Groq + Streamlit  
> Powered by the Chinook SQLite database (sample business data)

---

## 🚀 Problem Statement

Non-technical stakeholders (like managers, marketers, and analysts) often struggle to retrieve insights from raw databases because they don't know SQL.

### 🔍 Example Problem:
> "Show me the top 5 customers by total invoice value"  
> "What are the monthly sales trends?"  
> "How many orders did we receive from each country?"

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
| Vector DB     | [FAISS](https://github.com/facebookresearch/faiss) |
| Frontend      | [Streamlit](https://streamlit.io/) |
| Database      | Chinook SQLite (sample DB)  |
| Language      | Python                      |

---

## 🧩 Features

- 🔍 Ask data-related questions in plain English
- 📜 Auto-generates SQL queries using RAG + LLM
- 💾 Executes queries on real data (Chinook DB)
- 📊 Displays tabular results in UI
- 🚫 Handles errors like invalid SQL or bad queries
- 🔐 Uses `.env` for API security

---

## 🧱 Folder Structure

```
ai-sql-agent/
├── data/
│   └── chinook.db              # SQLite database
├── vectorstore/
│   └── index.faiss             # FAISS vector index
├── scripts/
│   ├── create_vectorstore.py   # Generate vector embeddings
│   └── extract_schema.py       # Parse DB schema
├── app.py                      # Streamlit frontend
├── rag_sql_generator.py        # LangChain RAG logic
├── run_sql.py                  # SQL executor
├── requirements.txt
└── .env                        # Groq API Key
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

3. **Set your Groq API key**
   ```
   # .env file
   GROQ_API_KEY=your_groq_api_key_here
   ```

4. **Create vectorstore**
   ```bash
   python scripts/create_vectorstore.py
   ```

5. **Run the app**
   ```bash
   streamlit run app.py
   ```

---

## 📸 UI Preview

> ![Preview](preview_screenshot.png)

---

## 🧠 Powered By

- LangChain for RAG
- FAISS for fast retrieval
- Groq for LLM response
- Streamlit for frontend

---

## 🙋‍♂️ Author

**Aditya Raj Singh**  
📍 GenAI & MERN Stack Developer  
🎓 KCC Institute of Technology and Management  
🔗 [LinkedIn](https://linkedin.com/in/your-profile)

---

## 📌 Future Work

- Support for other SQL databases (PostgreSQL, MySQL)
- Natural language filtering & grouping
- Chart/graph visualizations using Plotly/Altair
- User query history and logs

---

## ⭐️ If you liked this project

- Drop a ⭐️ on GitHub
- Connect with me on LinkedIn
- Fork and extend it!
