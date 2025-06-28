import os
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_groq import ChatGroq
from run_sql import run_sql_query


# Load environment variables
load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# Load FAISS vector store
def load_vectorstore():
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.load_local(
        "vectorstore/faiss_index",
        embeddings,
        allow_dangerous_deserialization=True
    )
    return vectorstore

# Prompt Template
prompt = PromptTemplate.from_template("""
You are an expert SQL assistant for a business dashboard.
Use the schema below to answer the user's question by writing a correct SQL query.

Rules:
- Only use columns and tables that exist in the schema.
- Do not assume columns like "total" exist — calculate them if needed.
- If you need to compute total invoice, use: `UnitPrice * Quantity`
- Use JOINs correctly with table relationships (e.g., Invoice → InvoiceLine → Customer).
- Use aliases like `i`, `il`, and `c` where needed for clarity.
- Return ONLY the SQL query, in a code block formatted like ```sql ... ``` — nothing else.

Schema:
{schema}

User Question:
{question}

Output the SQL inside a ```sql code block.
""")

# Initialize Groq LLM (LLaMA3)
llm = ChatGroq(
    temperature=0,
    model_name="llama3-8b-8192"
)

# Main RAG function
def extract_sql(text):
    """Extract SQL query from markdown-style code block."""
    import re
    match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()  # fallback if no code block

def generate_sql(question: str) -> str:
    retriever = load_vectorstore().as_retriever()
    docs = retriever.invoke(question)
    schema_text = "\n\n".join([doc.page_content for doc in docs])

    chain = prompt | llm
    result = chain.invoke({
        "schema": schema_text,
        "question": question
    })

    return extract_sql(result.content)

