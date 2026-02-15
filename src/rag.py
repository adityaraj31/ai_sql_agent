
import re
from typing import Optional
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from src.config import (
    GROQ_API_KEY, 
    PINECONE_INDEX_NAME, 
    EMBEDDING_MODEL_NAME, 
    LLM_MODEL_NAME
)

import streamlit as st
import time

@st.cache_resource
def get_embeddings():
    print("🚀 Starting: Loading Embeddings...")
    start_time = time.time()
    # No API key needed for local HF model
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    print(f"✅ Finished: Embeddings loaded in {time.time() - start_time:.2f}s")
    return embeddings

@st.cache_resource
def get_vectorstore():
    print("🚀 Starting: Connecting to Pinecone...")
    start_time = time.time()
    embeddings = get_embeddings()
    vectorstore = PineconeVectorStore.from_existing_index(
        index_name=PINECONE_INDEX_NAME,
        embedding=embeddings
    )
    print(f"✅ Finished: VectorStore connected in {time.time() - start_time:.2f}s")
    return vectorstore

def get_llm():
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set")
    return ChatGroq(
        temperature=0,
        model_name=LLM_MODEL_NAME,
        api_key=GROQ_API_KEY
    )

def extract_sql(text: str) -> str:
    """Extract SQL query from markdown-style code block."""
    match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: check if the text itself looks like SQL (starts with SELECT/WITH)
    text = text.strip()
    if text.upper().startswith("SELECT") or text.upper().startswith("WITH"):
        return text
    return text



def get_chat_history_str(chat_history: list) -> str:
    """
    Helper to format chat history for the prompt.
    EXPECTS: list of dicts or tuples. 
    If dict: {'role': 'user', 'content': 'msg', 'sql': 'optional_sql'}
    """
    if not chat_history:
        return "No history."
    
    formatted_history = []
    for msg in chat_history[-6:]: 
        # Handle both dicts and tuples for backward compatibility or ease of use
        if isinstance(msg, dict):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            sql = msg.get("sql", None)
        elif isinstance(msg, (tuple, list)) and len(msg) >= 2:
            role = msg[0]
            content = msg[1]
            sql = None
        else:
            continue
            
        formatted_entry = f"{role.capitalize()}: {content}"
        if sql:
            formatted_entry += f"\n(Context SQL: {sql})"
        
        formatted_history.append(formatted_entry)
        
    return "\n".join(formatted_history)

def detect_comparison_keywords(question: str) -> tuple:
    """
    Detect if user is asking for a comparison.
    Returns: (is_comparison, comparison_type)
    """
    question_lower = question.lower()
    keywords = {
        'vs': 'versus', 'versus': 'versus', 'compared to': 'comparison',
        'compared with': 'comparison', 'difference': 'difference', 'growth': 'growth',
        'change': 'change', 'increased': 'trend', 'decreased': 'trend',
        'higher': 'comparison', 'lower': 'comparison', 'improvement': 'trend',
        'decline': 'trend', 'quarter': 'time_period', 'month': 'time_period',
        'year': 'time_period', 'last': 'time_reference', 'previous': 'time_reference'
    }
    
    for keyword, comp_type in keywords.items():
        if keyword in question_lower:
            return True, comp_type
    return False, None

def reformulate_question(question: str, chat_history: list) -> str:
    """
    Uses the LLM to rewrite a follow-up question into a standalone question.
    Handles comparisons, temporal references, and context-dependent pronouns.
    """
    if not chat_history:
        return question

    history_str = get_chat_history_str(chat_history)
    is_comparison, comp_type = detect_comparison_keywords(question)
    
    comparison_context = ""
    if is_comparison:
        comparison_context = f"""
    
    IMPORTANT: The user is asking for a COMPARISON (type: {comp_type}).
    When you detect comparison keywords like 'vs', 'compared to', 'growth', 'change', etc:
    - Identify what is being compared (time periods, groups, metrics, etc.)
    - Include BOTH the current state AND the comparison baseline
    - Examples:
      * "vs last quarter" → include current quarter AND previous quarter
      * "how much higher" → compare the two values
      * "growth vs last year" → year-over-year comparison"""
    
    prompt = PromptTemplate.from_template("""
    You are a helpful assistant rewriting questions to be standalone, understanding context and comparisons.
    
    Context History:
    {history}
    
    Latest User Question: {question}
    {comparison_context}
    
    Task:
    Rewrite the "Latest User Question" into a standalone question that:
    1. Captures context from history (especially previous SQL queries and results)
    2. Resolves pronouns: "their" = the entities from previous query, "it" = previous metric
    3. Includes temporal context: "last quarter" relative to current period
    4. For comparisons: specifies BOTH items being compared
    
    Examples:
    History: User asked "Show sales by region"
    Question: "How much higher was North vs South?"
    Reformulated: "What are the total sales for North region compared to South region?"
    
    History: User asked "Q4 revenue"
    Question: "How much did we grow?"
    Reformulated: "What is the growth rate comparing Q4 revenue to Q3 revenue?"
    
    Output ONLY the reformulated question, no explanations.
    """)
    
    llm = get_llm()
    chain = prompt | llm
    
    response = chain.invoke({
        "history": history_str,
        "question": question,
        "comparison_context": comparison_context
    })
    
    refined_question = response.content.strip()
    print(f"📝 Reformulated: '{question}' -> '{refined_question}'")
    if is_comparison:
        print(f"   🔄 Comparison detected: {comp_type}")
    return refined_question

def generate_sql(question: str, chat_history: list = None) -> str:
    """
    Generates a SQL query based on the user question and schema.
    Handles follow-up questions by reformulating them first.
    """
    if chat_history is None:
        chat_history = []
        
    # Step 1: Reformulate the question (handling "it", "them", etc.)
    refined_question = reformulate_question(question, chat_history)
    
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever()
    
    # Step 2: Retrieve relevant schema using the CLEAN question
    docs = retriever.invoke(refined_question)
    schema_text = "\n\n".join([doc.page_content for doc in docs])
    
    # Extract table names roughly for logging
    table_names = [doc.page_content.split('(')[0].strip() for doc in docs]
    print(f"Retrieved {len(docs)} schema documents: {table_names}")
    
    prompt = PromptTemplate.from_template("""
    You are an expert SQL assistant skilled in business analysis and comparisons.
    Use the schema below to answer the user's question by writing a correct SQL query.
    
    Rules:
    - GENERATE ONLY READ-ONLY SQL (SELECT, WITH, PRAGMA). DO NOT generate UPDATE, DELETE, DROP, INSERT, or ALTER statements.
    - **dialect: SQLite**. Do NOT use `TOP n`. Use `LIMIT n` at the end of the query.
    - **Date Handling**: For extracting year/month, use SQLite's `strftime('%Y-%m', DateColumn)`. For year, use `strftime('%Y', DateColumn)`.
    - **Comparisons**: When user asks to compare two periods/groups:
      * Use UNION or JOIN to show both periods side-by-side with clear aliases
      * Examples: 'current_period' vs 'previous_period', 'group_a' vs 'group_b', 'this_year' vs 'last_year'
      * Calculate differences/growth when asked: (current - previous) / previous * 100 AS growth_pct
      * Order results logically (e.g., chronologically or by metric value)
    - **Temporal Queries**: 
      * IMPORTANT: The database is HISTORICAL. It contains data only from **2009 to 2013**.
      * If the user asks for "today", "now", or relative periods like "last quarter" without context, assume "today" is **2013-12-31**.
      * "Last quarter" = Oct-Dec 2013.
      * "Last year" = 2012.
      * Be precise with date ranges and ALWAYS use `strftime` for SQLite date comparisons.
    - **Ambiguity**: If the user asks for "best" or "top" without a specific metric, assume "Total Sales" or "Count" with clear aliases.
    - **Refusal**: If the question is completely unrelated to the database (e.g., "capital of France"), return: `SELECT 'I can only answer questions about the connected database.' AS Service_Message;`
    - Only use columns and tables that exist in the schema.
    - Do not assume columns like "total" exist — calculate them if needed.
    - Use JOINs correctly based on foreign keys defined in the schema.
    - Use sensible aliases for tables (e.g., first letter of table name) for clarity.
    - Return ONLY the SQL query, in a code block formatted like ```sql ... ``` — nothing else.
    - Only use columns and tables that exist in the schema.
    - Do not assume columns like "total" exist — calculate them if needed.
    - Do not assume columns like "total" exist — calculate them if needed.
    - Use JOINs correctly based on foreign keys defined in the schema.
    - Use sensible aliases for tables (e.g., first letter of table name) for clarity.
    - Return ONLY the SQL query, in a code block formatted like ```sql ... ``` — nothing else.
    
    Schema:
    {schema}
    
    User Question:
    {question}
    
    Output the SQL inside a ```sql code block.
    """)
    
    llm = get_llm()
    chain = prompt | llm
    
    result = chain.invoke({
        "schema": schema_text,
        "question": refined_question # Pass the refined question to the generator
    })

    sql_start_marker = "```sql"
    sql_end_marker = "```"
    raw_content = result.content
    print(f"LLM Raw Response:\n{raw_content}\n")
    
    final_sql = extract_sql(raw_content)
    print(f"Extracted SQL:\n{final_sql}\n")

    return final_sql
