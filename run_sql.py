import sqlite3

def run_sql_query(db_path: str, query: str):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        return [dict(zip(columns, row)) for row in rows], None  # no error
    except Exception as e:
        return None, str(e)  # return error message
