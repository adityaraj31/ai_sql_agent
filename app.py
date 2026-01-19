
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
Ask questions in plain English and get SQL queries + results from the connected database. 
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

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sql" in message:
            st.code(message["sql"], language="sql")
        if "results" in message:
            st.dataframe(message["results"], width="stretch")
        if "chart" in message and message["chart"]:
            st.plotly_chart(message["chart"], width="stretch")

# React to user input
if prompt := st.chat_input("Ask a question data (e.g., 'Show top 5 customers')"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare chat history for RAG (pass full objects)
    chat_history = st.session_state.messages

    # Generate SQL
    with st.spinner("Analyzing request..."):
        try:
            sql_query = generate_sql(prompt, chat_history)
        except Exception as e:
            st.error(f"Error generating SQL: {e}")
            sql_query = None

    if sql_query:
        # Display Assistant Response Logic
        with st.chat_message("assistant"):
            st.markdown(f"**Generated SQL:**")
            st.code(sql_query, language="sql")
            
            with st.spinner("Running query..."):
                results, error = run_sql_query(sql_query)
            
            # Debugging outputs
            print(f"Query Result:\n{results}")
            if error:
                print(f"Query Error:\n{error}")

            response_content = ""
            current_response = {"role": "assistant", "content": "Here are the results:", "sql": sql_query}

            if error:
                st.error(f"❌ Execution Error: {error}")
                response_content = f"Error: {error}"
                log_query(prompt, sql_query, success=False, error_message=error)
            elif results:
                df = pd.DataFrame(results)
                st.dataframe(df, width="stretch")
                current_response["results"] = df
                
                log_query(prompt, sql_query, success=True)
                
                # Visualizations
                with st.spinner("Checking for visualizations..."):
                    viz_config = analyze_data_for_chart(prompt, df)
                    if viz_config:
                        chart = render_chart(df, viz_config)
                        if chart:
                            st.plotly_chart(chart, width="stretch")
                            current_response["chart"] = chart

            else:
                st.warning("Query returned no results.")
                response_content = "Query returned no results."
                log_query(prompt, sql_query, success=True, error_message="No results")

            # Add assistant response to chat history
            st.session_state.messages.append(current_response)

# Footer
st.markdown("---")
st.caption("AI SQL Agent - Built with Modern Stack")
