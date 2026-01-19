
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

def reformulate_question(question: str, chat_history: list) -> str:
    """
    Uses the LLM to rewrite a follow-up question into a standalone question.
    """
    if not chat_history:
        return question

    history_str = get_chat_history_str(chat_history)
    
    prompt = PromptTemplate.from_template("""
    You are a helpful assistant rewriting questions to be standalone.
    
    Context History:
    {history}
    
    Latest User Question: {question}
    
    Task:
    Rewrite the "Latest User Question" into a standalone question that captures the context from the history (especially previous SQL queries).
    If the user says "their" or "it", refer to the specific data fetched in the previous SQL query.
    
    Example:
    History: 
    User: Top 5 customers
    Assistant: (SQL: SELECT Name FROM Customer LIMIT 5)
    User: What are their emails?
    
    Reformulated: What are the emails of the top 5 customers identified in the previous query?
    
    Output ONLY the reformulated question.
    """)
    
    llm = get_llm()
    chain = prompt | llm
    
    response = chain.invoke({
        "history": history_str,
        "question": question
    })
    
    refined_question = response.content.strip()
    print(f"Reformulated: '{question}' -> '{refined_question}'")
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
    You are an expert SQL assistant.
    Use the schema below to answer the user's question by writing a correct SQL query.
    
    Rules:
    - GENERATE ONLY READ-ONLY SQL (SELECT, WITH, PRAGMA). DO NOT generate UPDATE, DELETE, DROP, INSERT, or ALTER statements.
    - **dialect: SQLite**. Do NOT use `TOP n`. Use `LIMIT n` at the end of the query.
    - **Date Handling**: For extracting year/month, use SQLite's `strftime('%Y-%m', DateColumn)`.
    - **Ambiguity**: If the user asks for "best" or "top" without a specific metric, assume "Total Sales" or "Count" and alias the column clearly.
    - **Refusal**: If the question is completely unrelated to the database (e.g., "capital of France"), return: `SELECT 'I can only answer questions about the connected database.' AS Service_Message;`
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
