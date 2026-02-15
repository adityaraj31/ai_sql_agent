
import json
import re
import pandas as pd
import plotly.express as px
from typing import Optional, Dict, Any
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from src.config import GROQ_API_KEY, LLM_MODEL_NAME

def get_visualization_llm():
    """Returns an instance of ChatGroq for visualization tasks."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set")
        
    return ChatGroq(
        temperature=0,
        model_name=LLM_MODEL_NAME,
        api_key=GROQ_API_KEY
    )

def analyze_data_for_chart(question: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Analyzes the dataframe and user question to determine the best chart type.
    Returns specific configuration for Plotly.
    """
    # Relaxation: Allow single row if multiple numeric columns exist (Comparison)
    if df.empty or (len(df) < 2 and len(df.select_dtypes(include=['number']).columns) < 2):
        return None

    columns = df.columns.tolist()
    # Take a small sample to give context to the LLM
    data_sample = df.head(3).to_dict(orient='records')
    
    prompt = PromptTemplate.from_template("""
    You are a data visualization expert.
    
    User Question: {question}
    Data Columns: {columns}
    Data Sample: {data_sample}
    
    Determine if this data should be visualized.
    If yes, choose the best chart type from: ['bar', 'line', 'pie', 'scatter'].
    
    Rules:
    - Comparison of categories -> 'bar'
    - Trends over time (dates/years) -> 'line'
    - Distribution of parts to whole -> 'pie'
    - Correlation between two numbers -> 'scatter'
    - **Wide-Format Single Row**: If there is only 1 row but multiple metric columns (e.g., current_sales, previous_sales), use 'bar' and set:
      * "chart_type": "bar"
      * "x_axis": "__columns__" (special marker to use column names as categories)
      * "y_axis": "__values__" (special marker to use values from that single row)
    
    Return ONLY a JSON object with this format:
    {{
        "chart_type": "bar/line/pie/scatter/none",
        "x_axis": "column_name_for_x",
        "y_axis": "column_name_for_y",
        "title": "A short descriptive title for the chart"
    }}
    """)
    
    llm = get_visualization_llm()
    chain = prompt | llm
    
    try:
        response = chain.invoke({
            "question": question,
            "columns": columns,
            "data_sample": data_sample
        })
        
        content = response.content
        
        # Robust JSON extraction
        match = re.search(r"```(?:json)?\s*({.*?})\s*```", content, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            match = re.search(r"({.*})", content, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                return None

        config = json.loads(json_str)
        print(f"Visualization Config generated: {config}")
        
        if config.get('chart_type') == 'none':
            return None
            
        return config
    except Exception as e:
        print(f"Error in visualization analysis: {e}")
        return None

def render_chart(df: pd.DataFrame, config: dict):
    """
    Generates a Plotly figure based on the config.
    Handles special markers for wide-format single-row data.
    """
    chart_type = config.get('chart_type')
    x = config.get('x_axis')
    y = config.get('y_axis')
    title = config.get('title', 'Chart')
    
    # Handle wide-format (single row with multiple metrics)
    if x == "__columns__" and y == "__values__" and len(df) == 1:
        # Transform 1-row wide DF to 2-column long DF
        metric_cols = df.select_dtypes(include=['number']).columns.tolist()
        df_long = pd.DataFrame({
            'Metric': metric_cols,
            'Value': [df.iloc[0][col] for col in metric_cols]
        })
        x, y = 'Metric', 'Value'
        df = df_long

    if x not in df.columns or (y and y not in df.columns):
         # invalid columns predicted
         return None

    try:
        if chart_type == "bar":
            fig = px.bar(df, x=x, y=y, title=title, template="plotly_dark")
        elif chart_type == "line":
            fig = px.line(df, x=x, y=y, title=title, markers=True, template="plotly_dark")
        elif chart_type == "pie":
            fig = px.pie(df, names=x, values=y, title=title, template="plotly_dark")
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x, y=y, title=title, template="plotly_dark")
        else:
            return None
            
        # UI Polish: Hide axis labels if not needed
        fig.update_layout(xaxis_title="", yaxis_title="")
        return fig
    except Exception as e:
        print(f"Error rendering chart: {e}")
        return None
