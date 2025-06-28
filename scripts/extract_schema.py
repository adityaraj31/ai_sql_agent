import sqlite3

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
        doc = f"Table: {table}\nColumns:\n{col_info}"
        docs.append(doc)

    conn.close()
    return docs

if __name__ == "__main__":
    schema_docs = extract_schema("data/chinook.db")
    for doc in schema_docs:
        print(doc)
