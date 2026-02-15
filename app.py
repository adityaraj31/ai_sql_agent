
import streamlit as st
import pandas as pd
import requests
import json
import os
import time
from src.visualization import analyze_data_for_chart, render_chart

# Initialize LangSmith Tracing
from src.config import (
    LANGCHAIN_TRACING_V2, 
    LANGCHAIN_API_KEY, 
    LANGCHAIN_PROJECT,
    LANGCHAIN_ENDPOINT
)

if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT

# FastAPI backend URL
API_BASE_URL = "http://localhost:8000"

# Page Configuration
st.set_page_config(
    page_title="AI SQL Agent", 
    layout="wide",
    page_icon="🔍"
)

# --- Custom CSS for Claude-style Minimalist UI ---
st.markdown("""
    <style>
    /* Show Streamlit Header but make it transparent */
    header[data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
        color: white !important;
    }
    
    /* Hide specific Streamlit elements but keep the sidebar toggle */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Global Background & Font */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
        font-family: 'Inter', sans-serif;
    }
    
    /* Centered Greeting & Minimalist Layout */
    .greeting-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 60vh;
        text-align: center;
    }
    .greeting-text {
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, #58a6ff, #bc8cff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-greeting {
        font-size: 1.2rem;
        color: #8b949e;
        margin-bottom: 2rem;
    }
    
    /* Style the Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Chat Input Styling */
    .stChatInputContainer {
        padding-bottom: 2rem;
        background-color: transparent !important;
    }
    
    /* Chat Bubbles */
    .stChatMessage {
        background-color: transparent !important;
        border-bottom: 1px solid #21262d;
        padding: 1.5rem 0;
    }
    
    /* Results Styling */
    .stDataFrame {
        border-radius: 8px;
        border: 1px solid #30363d;
    }
    
    /* Specific styling for Top-Right Button */
    .stButton > button {
        border-radius: 20px !important;
        font-weight: 600 !important;
    }

    /* Auto-scroll anchor */
    .stChatMessageContainer {
        overflow-anchor: auto !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar: History & Settings ---
with st.sidebar:
    # Move New Chat to Sidebar (as requested)
    if st.button("➕ New Chat", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    st.title("📜 History")
    
    if st.button("🔥 Clear DB History", use_container_width=True):
        try:
            response = requests.delete(f"{API_BASE_URL}/history", timeout=5)
            if response.status_code == 200:
                st.success("History cleared!")
                st.rerun()
            else:
                st.error("Failed to clear history")
        except Exception as e:
            st.error(f"Error: {e}")
    
    st.divider()

try:
    response = requests.get(f"{API_BASE_URL}/history", timeout=5)
    if response.status_code == 200:
        history_data = response.json()
        logs = history_data.get("logs", [])
    else:
        logs = []
        st.sidebar.error("Failed to fetch history from API")
except Exception as e:
    logs = []
    st.sidebar.error(f"API Error: {e}")

if logs:
    # Show internal logic logs in reverse order - Titles only (no timestamps)
    for log in reversed(logs[-10:]):
        display_title = log['question'] if len(log['question']) < 30 else f"{log['question'][:27]}..."
        with st.sidebar.expander(display_title):
            st.write(f"**Q:** {log['question']}")
            st.code(log['sql_query'], language="sql")
            st.caption(f"Status: {'✅ Success' if log['success'] else '❌ Failed'}")
else:
    st.sidebar.info("No queries yet.")

# --- Main Interface ---

if "messages" not in st.session_state:
    st.session_state.messages = []

# Show Greeting only if no messages
if not st.session_state.messages:
    st.markdown("""
        <div class="greeting-container">
            <div class="greeting-text">How can I help you with data today?</div>
            <div class="sub-greeting">Ask anything from the Chinook database—sales, trends, or customer insights.</div>
        </div>
    """, unsafe_allow_html=True)

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

    # Prepare chat history for API - exclude non-serializable objects
    # CRITICAL: We only send PAST messages. The current prompt is handled separately by the backend.
    chat_history = []
    # Use st.session_state.messages[:-1] to exclude the message we just added
    for msg in st.session_state.messages[:-1]:
        chat_msg = {
            "role": msg["role"],
            "content": msg["content"]
        }
        # Only include sql if it exists
        if "sql" in msg:
            chat_msg["sql"] = msg["sql"]
        # Convert results to list of dicts if they're DataFrames
        if "results" in msg:
            if isinstance(msg["results"], pd.DataFrame):
                chat_msg["results"] = msg["results"].to_dict(orient='records')
            else:
                chat_msg["results"] = msg["results"]
        chat_history.append(chat_msg)

    # Generate SQL via API
    with st.spinner("Analyzing request..."):
        try:
            payload = {
                "question": prompt,
                "chat_history": chat_history
            }
            response = requests.post(
                f"{API_BASE_URL}/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                api_response = response.json()
            else:
                api_response = {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                    "message": response.text
                }
        except requests.exceptions.Timeout:
            api_response = {
                "success": False,
                "error": "Request timeout",
                "message": "The API took too long to respond. Make sure the server is running on http://localhost:8000"
            }
        except Exception as e:
            api_response = {
                "success": False,
                "error": "Connection error",
                "message": f"{str(e)}. Make sure the FastAPI server is running on http://localhost:8000"
            }

    if not api_response.get("success"):
        st.error(f"❌ Error: {api_response.get('error', 'Unknown error')}")
        st.error(f"Details: {api_response.get('message', '')}")
    else:
        sql_query = api_response.get("sql_query")
        results = api_response.get("results")
        
        # Display Assistant Response Logic with Streaming Effect
        with st.chat_message("assistant"):
            # Helper generator for streaming text
            def stream_text(text: str):
                for word in text.split(" "):
                    yield word + " "
                    time.sleep(0.05)

            st.markdown(f"**Generated SQL:**")
            st.code(sql_query, language="sql")
            
            # Stream the "Here are the results" message or any other info
            st.write_stream(stream_text("Here are the results:"))
            
            current_response = {"role": "assistant", "content": "Here are the results:", "sql": sql_query}

            if results:
                df = pd.DataFrame(results)
                st.dataframe(df, width="stretch")
                current_response["results"] = df
                
                # Visualizations
                with st.spinner("Checking for visualizations..."):
                    viz_config = analyze_data_for_chart(prompt, df)
                    if viz_config:
                        chart = render_chart(df, viz_config)
                        if chart:
                            st.plotly_chart(chart, width="stretch")
                            current_response["chart"] = chart
                
                # Add Download CSV button
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Results as CSV",
                    data=csv,
                    file_name='query_results.csv',
                    mime='text/csv',
                )

            else:
                st.warning("Query returned no results.")
                current_response["content"] = "Query returned no results."

            # Add assistant response to chat history
            st.session_state.messages.append(current_response)

# Footer
st.markdown("---")
st.caption("AI SQL Agent - Built with Modern Stack")
