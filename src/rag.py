import sys
import logging
import re
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from src.config import (
    GROQ_API_KEY,
    LLM_MODEL_NAME,
    DB_TYPE,
)
from src.graphrag import (
    retrieve_schema_context,
    get_full_schema_text as get_schema_as_text,
)
from src.llm import get_llm

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_session_title(first_message: str) -> str:
    """
    Generate a short, descriptive title for a chat session using LLM.
    Returns a title that summarizes the user's first question.
    """
    if not first_message or len(first_message.strip()) < 3:
        return "New Chat"

    prompt = PromptTemplate.from_template("""
You are a helpful assistant. Create a short, descriptive title (max 50 characters) 
for a chat session based on the user's first message.

User Message: {message}

Generate a concise title that captures the essence of what they want to know.
Examples:
- "Sales by Region" 
- "Customer Count Analysis"
- "Q4 Revenue Comparison"
- "Top 10 Albums"

Output ONLY the title, no quotes or explanation.
""")

    try:
        llm = get_llm()
        chain = prompt | llm
        response = chain.invoke({"message": first_message})
        title = response.content.strip()[:50]

        if not title:
            return "New Chat"

        logger.info(f"Generated session title: '{title}'")
        return title
    except Exception as e:
        logger.warning(f"Failed to generate title: {e}")
        return first_message[:40] + "..." if len(first_message) > 40 else first_message


def get_llm():
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set")
    return ChatGroq(temperature=0, model=LLM_MODEL_NAME, api_key=GROQ_API_KEY)


def extract_sql(text: str) -> str:
    """Extract SQL query from markdown-style code block."""
    match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    text = text.strip()
    if text.upper().startswith("SELECT") or text.upper().startswith("WITH"):
        return text
    return text


def get_chat_history_str(chat_history: list) -> str:
    """
    Format chat history for the prompt.
    Includes previous SQL queries so the LLM can reuse correct join patterns.
    """
    if not chat_history:
        return "No history."

    formatted_history = []
    for msg in chat_history[-6:]:
        if isinstance(msg, dict):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            sql = msg.get("sql", None)
        elif isinstance(msg, (tuple, list)) and len(msg) >= 2:
            role = msg[0]
            content = msg[1]
            sql = None
        else:
            continue

        formatted_entry = f"{role.capitalize()}: {content}"
        if sql:
            formatted_entry += f"\n(Previous SQL used:\n{sql}\n)"

        formatted_history.append(formatted_entry)

    return "\n".join(formatted_history)


def get_last_sql(chat_history: list) -> Optional[str]:
    """
    Extract the most recent SQL query from chat history.
    Used to give the SQL generator explicit context about correct join patterns.
    """
    for msg in reversed(chat_history):
        if isinstance(msg, dict):
            sql = msg.get("sql")
            if sql:
                return sql
    return None


def detect_comparison_keywords(question: str) -> tuple:
    """Detect if user is asking for a comparison."""
    question_lower = question.lower()
    keywords = {
        "vs": "versus",
        "versus": "versus",
        "compared to": "comparison",
        "compared with": "comparison",
        "difference": "difference",
        "growth": "growth",
        "change": "change",
        "increased": "trend",
        "decreased": "trend",
        "higher": "comparison",
        "lower": "comparison",
        "improvement": "trend",
        "decline": "trend",
        "quarter": "time_period",
        "month": "time_period",
        "year": "time_period",
        "last": "time_reference",
        "previous": "time_reference",
    }
    for keyword, comp_type in keywords.items():
        if keyword in question_lower:
            return True, comp_type
    return False, None


def reformulate_question(question: str, chat_history: list) -> str:
    """
    Rewrites a follow-up question into a fully standalone question,
    resolving pronouns and carrying forward context from history.
    """
    if not chat_history:
        return question

    history_str = get_chat_history_str(chat_history)
    is_comparison, comp_type = detect_comparison_keywords(question)

    comparison_context = ""
    if is_comparison:
        comparison_context = f"""

    IMPORTANT: The user is asking for a COMPARISON (type: {comp_type}).
    When you detect comparison keywords like 'vs', 'compared to', 'growth', 'change', etc:
    - Identify what is being compared (time periods, groups, metrics, etc.)
    - Include BOTH the current state AND the comparison baseline
    - Examples:
      * "vs last quarter" → include current quarter AND previous quarter
      * "how much higher" → compare the two values
      * "growth vs last year" → year-over-year comparison"""

    prompt = PromptTemplate.from_template("""
    You are a helpful assistant rewriting questions to be standalone, understanding context and comparisons.

    Context History:
    {history}

    Latest User Question: {question}
    {comparison_context}

    Task:
    Rewrite the "Latest User Question" into a standalone question that:
    1. Captures context from history (especially previous SQL queries and results)
    2. Resolves pronouns: "their" = the entities from previous query, "it" = previous metric
    3. Includes temporal context: "last quarter" relative to current period
    4. For comparisons: specifies BOTH items being compared

    Examples:
    History: User asked "Show sales by region"
    Question: "How much higher was North vs South?"
    Reformulated: "What are the total sales for North region compared to South region?"

    History: User asked "Q4 revenue"
    Question: "How much did we grow?"
    Reformulated: "What is the growth rate comparing Q4 revenue to Q3 revenue?"

    Output ONLY the reformulated question, no explanations.
    """)

    llm = get_llm()
    response = (prompt | llm).invoke(
        {
            "history": history_str,
            "question": question,
            "comparison_context": comparison_context,
        }
    )

    refined_question = response.content.strip()
    logger.info(f"Reformulated: '{question}' -> '{refined_question}'")
    if is_comparison:
        logger.info(f"   Comparison detected: {comp_type}")
    return refined_question


def check_question_relevance(question: str, schema_text: str) -> tuple[bool, str]:
    """
    Check if the question is relevant to the database schema.
    Returns: (is_relevant, message)
    """
    if not schema_text:
        return True, ""

    prompt = PromptTemplate.from_template("""
You are a helpful database assistant. Determine if the user's question can be answered using the provided database schema.

Schema:
{schema}

User Question: {question}

Instructions:
- If the question is about database records, data, tables, or can be answered with SQL queries, return: RELEVANT
- If the question is about general knowledge unrelated to the database (e.g., "capital of France", "weather", "history", "mathematics", "coding help for other languages"), return: IRRELEVANT
- If the question asks to do something other than reading data (e.g., "delete all records", "update prices"), return: IRRELEVANT

Output ONLY one word: RELEVANT or IRRELEVANT
""")

    llm = get_llm()
    chain = prompt | llm

    result = chain.invoke({"schema": schema_text, "question": question})
    response = result.content.strip().upper()

    is_relevant = "RELEVANT" in response
    logger.info(f"Question relevance check: {is_relevant} for question: '{question}'")

    return is_relevant, ""


def generate_sql(question: str, chat_history: list = None) -> str:
    """
    Generates a SQL query based on the user question and schema.

    Fix: The previous SQL from chat_history is now explicitly passed into the
    SQL generation prompt. This prevents the LLM from re-deriving joins from
    scratch on follow-up questions, which caused incorrect join paths
    (e.g. u.id = p.subscription_id instead of going through subscriptions).
    """
    if chat_history is None:
        chat_history = []

    # Step 1: Reformulate the question (resolve "their", "it", etc.)
    refined_question = reformulate_question(question, chat_history)

    # Step 2: Retrieve relevant schema via GraphRAG (Neo4j)
    try:
        schema_text = retrieve_schema_context(refined_question)
        logger.info("Retrieved schema from Neo4j graph.")
    except Exception as e:
        logger.warning(f"GraphRAG retrieval failed: {e} — falling back to full schema")
        schema_text = get_schema_as_text()

    # Step 3: Extract the last SQL from history to anchor join patterns
    # ─────────────────────────────────────────────────────────────────
    # Root cause of the bad-JOIN bug: follow-up queries were generated
    # without seeing the previous SQL, so the LLM guessed joins instead
    # of reusing the correct paths from the prior query.
    last_sql = get_last_sql(chat_history)
    previous_sql_block = (
        f"\nPrevious SQL Query (reuse its JOIN pattern when relevant):\n"
        f"```sql\n{last_sql}\n```\n"
        if last_sql
        else ""
    )
    # ─────────────────────────────────────────────────────────────────

    # Build dialect-specific instructions
    if DB_TYPE == "postgres":
        dialect_instructions = """
    - **dialect: PostgreSQL**. Use `LIMIT n` or `FETCH FIRST n ROWS ONLY` for limiting results.
    - **Date Handling**: Use `EXTRACT(YEAR FROM col)` or `TO_CHAR(col, 'YYYY-MM')`.
    - **Case Sensitivity**: Use ILIKE for case-insensitive pattern matching.
    - **Boolean**: PostgreSQL uses TRUE/FALSE (not 1/0).
        """
    else:
        dialect_instructions = """
    - **dialect: SQLite**. Do NOT use `TOP n`. Use `LIMIT n` at the end of the query.
    - **Date Handling**: Use SQLite's `strftime('%Y-%m', col)` for year/month.
        """

    prompt = PromptTemplate.from_template(
        """
    You are an expert SQL assistant skilled in business analysis and comparisons.
    Use the schema below to answer the user's question by writing a correct SQL query.

    Rules:
    - GENERATE ONLY READ-ONLY SQL (SELECT, WITH). DO NOT generate UPDATE, DELETE, DROP, INSERT, or ALTER.
    """
        + dialect_instructions
        + """
    - **Follow-up queries**: If a "Previous SQL Query" is provided, reuse its exact JOIN
      structure for any tables it already joins. Do NOT re-derive join paths from scratch.
    - **Comparisons**: Use UNION or JOIN to show both periods side-by-side with clear aliases.
      Calculate differences when asked: (current - previous) / previous * 100 AS growth_pct.
    - **Ambiguity**: If the user asks for "best" or "top" without a metric, assume total amount or count.
    - **Refusal**: If the question is unrelated to the database, return:
      `SELECT 'I can only answer questions about the connected database.' AS Service_Message;`
    - Only use columns and tables present in the schema.
    - Do not assume columns like "total" exist — calculate them if needed.
    - Use sensible table aliases (e.g., first letter of table name).
    - Return ONLY the SQL query inside a ```sql ... ``` code block — nothing else.

    Schema:
    {schema}
    {previous_sql}
    User Question:
    {question}

    Output the SQL inside a ```sql code block.
    """
    )

    llm = get_llm()
    result = (prompt | llm).invoke(
        {
            "schema": schema_text,
            "previous_sql": previous_sql_block,
            "question": refined_question,
        }
    )

    logger.debug(f"LLM Raw Response:\n{result.content}\n")
    final_sql = extract_sql(result.content)
    logger.info(f"Extracted SQL:\n{final_sql}\n")
    return final_sql
