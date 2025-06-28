import os
import sqlite3
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document

def extract_schema(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    docs = []
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        col_info = "\n".join([f"- {col[1]} ({col[2]})" for col in columns])
        doc_text = f"Table: {table}\nColumns:\n{col_info}"
        docs.append(Document(page_content=doc_text))
    
    conn.close()
    return docs

def build_faiss_index():
    docs = extract_schema("data/chinook.db")

    # HuggingFace embedding model (you can change model_name if needed)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Create and save FAISS index
    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local("vectorstore/faiss_index")
    print("FAISS vector store created with Hugging Face embeddings.")

if __name__ == "__main__":
    build_faiss_index()
