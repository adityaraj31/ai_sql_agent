
import time
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone, ServerlessSpec
from src.config import (
    PINECONE_API_KEY, 
    PINECONE_INDEX_NAME, 
    PINECONE_DIMENSION, 
    PINECONE_METRIC, 
    PINECONE_CLOUD, 
    PINECONE_REGION,
    EMBEDDING_MODEL_NAME
)
from src.database import get_db_schema

def create_documents_from_schema() -> list[Document]:
    """Convert DB schema to a list of LangChain Documents."""
    schema = get_db_schema()
    docs = []
    for table, columns in schema.items():
        # columns is a list of "ColName (Type)"
        col_info = "\n".join([f"- {col}" for col in columns])
        content = f"Table: {table}\nColumns:\n{col_info}"
        docs.append(Document(page_content=content, metadata={"table": table}))
    return docs

def build_index():
    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY not found in environment variables.")

    print(f"Initializing Pinecone...")
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Check/Create Index
    existing_indexes = [i.name for i in pc.list_indexes()]
    if PINECONE_INDEX_NAME in existing_indexes:
        # We need to check if dimensions match, or just always recreate to be safe since we are switching back
        # The user might have a 768 dim index now. We need 384.
        # It is safer to delete and recreate.
        print(f"Deleting existing index {PINECONE_INDEX_NAME} to ensure correct dimensions (384)...")
        pc.delete_index(PINECONE_INDEX_NAME)
        time.sleep(10) # Wait for deletion to propagate

    print(f"Creating index: {PINECONE_INDEX_NAME}")
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=PINECONE_DIMENSION,
        metric=PINECONE_METRIC,
        spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION)
    )
    while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
        time.sleep(1)

    # Generate Docs
    print("Extracting schema...")
    docs = create_documents_from_schema()
    print(f"Found {len(docs)} tables.")

    # Embed and Upload
    print("Uploading to Pinecone (this may take a moment)...")
    
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    
    # We can use from_documents which handles batching usually
    PineconeVectorStore.from_documents(
        docs, 
        embeddings, 
        index_name=PINECONE_INDEX_NAME
    )
    print("Vector Store Successfully Updated!")

if __name__ == "__main__":
    build_index()
