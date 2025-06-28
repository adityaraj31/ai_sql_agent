import streamlit as st
from rag_sql_generator import generate_sql
from run_sql import run_sql_query

st.set_page_config(page_title="AI SQL Agent", layout="wide")

st.title("AI SQL Agent for Business Dashboard")
st.markdown("Ask a question in plain English and get SQL + results from the Chinook database.")

# 📝 User Input
question = st.text_input("Ask your question", placeholder="e.g., Show top 5 customers by purchase amount")

if question:
    with st.spinner("Generating SQL..."):
        sql_query = generate_sql(question)
        st.code(sql_query, language="sql")

        st.success("SQL query generated ✅")

        with st.spinner("Running SQL on database..."):
            results, error = run_sql_query("data/chinook.db", sql_query)

            if error:
                st.error(f"❌ SQL Execution Error:\n```\n{error}\n```")
            elif results:
                st.subheader("📊 Query Results")
                st.dataframe(results)
            else:
                st.warning("Query ran but returned no results.")
