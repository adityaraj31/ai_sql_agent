
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

def generate_sql(question: str) -> str:
    """
    Generates a SQL query based on the user question and schema.
    """
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever()
    
    # Retrieve relevant schema
    docs = retriever.invoke(question)
    schema_text = "\n\n".join([doc.page_content for doc in docs])
    
    prompt = PromptTemplate.from_template("""
    You are an expert SQL assistant for a business dashboard.
    Use the schema below to answer the user's question by writing a correct SQL query.
    
    Rules:
    - GENERATE ONLY READ-ONLY SQL (SELECT, WITH, PRAGMA). DO NOT generate UPDATE, DELETE, DROP, INSERT, or ALTER statements.
    - Only use columns and tables that exist in the schema.
    - Do not assume columns like "total" exist — calculate them if needed.
    - If you need to compute total invoice, use: `UnitPrice * Quantity`
    - Use JOINs correctly with table relationships (e.g., Invoice → InvoiceLine → Customer).
    - Use aliases like `i`, `il`, and `c` where needed for clarity.
    - Return ONLY the SQL query, in a code block formatted like ```sql ... ``` — nothing else.
    - If the question cannot be answered with the given schema, return a comment starting with -- explaining why.
    
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
        "question": question
    })

    return extract_sql(result.content)
