
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
    if df.empty or len(df) < 2:
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
    If the data is single-value or textual list that doesn't fit a chart, return 'none'.
    
    Rules:
    - Comparison of categories -> 'bar'
    - Trends over time (dates/years) -> 'line'
    - Distribution of parts to whole -> 'pie'
    - Correlation between two numbers -> 'scatter'
    
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
    """
    chart_type = config.get('chart_type')
    x = config.get('x_axis')
    y = config.get('y_axis')
    title = config.get('title', 'Chart')
    
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
            
        return fig
    except Exception as e:
        print(f"Error rendering chart: {e}")
        return None
