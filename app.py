
import streamlit as st
import pandas as pd
from src.rag import generate_sql
from src.database import run_sql_query
from src.logger import log_query, get_logs
from src.visualization import analyze_data_for_chart, render_chart

# Page Configuration
st.set_page_config(
    page_title="AI SQL Agent", 
    layout="wide",
    page_icon="🔍"
)

# Title and Description
st.title("🤖 AI SQL Agent")
st.markdown("""
Ask questions in plain English and get SQL queries + results from the Chinook database. 
Powered by **Llama3**, **LangChain**, and **Pinecone**.
""")

# --- Sidebar: Query History ---
st.sidebar.header("📜 Query History")
if st.sidebar.button("Refresh History"):
    st.rerun()

logs = get_logs()
if logs:
    # Show internal logic logs in reverse order
    for log in reversed(logs[-10:]):
        with st.sidebar.expander(f"{log['timestamp']} - {log['question'][:20]}..."):
            st.write(f"**Q:** {log['question']}")
            st.code(log['sql_query'], language="sql")
            st.caption(f"Status: {'✅ Success' if log['success'] else '❌ Failed'}")
else:
    st.sidebar.info("No queries yet.")

# --- Main Interface ---

question = st.text_input("Ask your question", placeholder="e.g., Show top 5 customers by purchase amount", key="user_question")

if question:
    # 1. Generate SQL
    st.subheader("1. Generated SQL")
    with st.spinner("Generating SQL query..."):
        try:
            sql_query = generate_sql(question)
            st.code(sql_query, language="sql")
        except Exception as e:
            st.error(f"Error generating SQL: {e}")
            sql_query = None

    # 2. Execute SQL
    if sql_query:
        st.subheader("2. Query Results")
        with st.spinner("Running query on database..."):
            results, error = run_sql_query(sql_query)

        if error:
            st.error(f"❌ SQL Execution Error:\n```\n{error}\n```")
            log_query(question, sql_query, success=False, error_message=error)
        elif results:
            # Display Data
            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True)
            
            log_query(question, sql_query, success=True)

            # 3. Visualization
            st.subheader("3. Visualization")
            with st.spinner("Analyzing data for visualization..."):
                viz_config = analyze_data_for_chart(question, df)
                
                if viz_config:
                    chart = render_chart(df, viz_config)
                    if chart:
                        st.plotly_chart(chart, use_container_width=True)
                    else:
                        st.info("Visualizer proposed a chart but failed to render it.")
                else:
                    st.info("No suitable visualization found for this data.")
                    
        else:
            st.warning("Query executed successfully but returned no results.")
            log_query(question, sql_query, success=True, error_message="No results returned")

# Footer
st.markdown("---")
st.caption("AI SQL Agent - Built with Modern Stack")
