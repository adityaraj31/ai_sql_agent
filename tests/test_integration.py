
import pytest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rag import generate_sql
from src.database import run_sql_query

@pytest.mark.parametrize("test_case", [
    {
        "name": "Simple Filtering (IN)",
        "question": "Show me all customers from Brazil or Canada.",
        "expected_min_rows": 1
    },
    {
        "name": "Date Filtering (Year)",
        "question": "Show all invoices from the year 2010.",
        "expected_min_rows": 1
    },
    {
        "name": "Pattern Matching (Fuzzy)",
        "question": "Find tracks with 'Love' in the title.",
        "expected_min_rows": 1
    },
    {
        "name": "Grouping (Count)",
        "question": "Count the number of customers in each country.",
        "expected_min_rows": 5 # Should be many countries
    },
    {
        "name": "Grouping + Having",
        "question": "Show countries that have more than 5 customers.",
        "expected_min_rows": 1
    },
    {
        "name": "Multi-Table Aggregation",
        "question": "What are the total sales for each Genre?",
        "expected_min_rows": 5
    }
])
def test_complex_natural_language_queries(test_case):
    """
    Integration test to verify the agent can handle various types of complex
    natural language questions by generating valid SQL and returning results.
    """
    print(f"\nRunning Test: {test_case['name']}")
    
    # 1. Generate SQL
    sql = generate_sql(test_case['question'])
    assert sql is not None, "SQL Generation failed (returned None)"
    assert len(sql) > 10, "SQL Generation returned suspiciously short string"
    assert "SELECT" in sql.upper(), "SQL must contain SELECT"
    
    # 2. Execute SQL
    results, error = run_sql_query(sql)
    assert error is None, f"SQL Execution failed: {error}"
    assert results is not None, "Results should not be None"
    
    # 3. Verify Results
    row_count = len(results)
    print(f"   Generated SQL: {sql}")
    print(f"   Rows returned: {row_count}")
    
    assert row_count >= test_case['expected_min_rows'], \
        f"Expected at least {test_case['expected_min_rows']} rows, but got {row_count}"

