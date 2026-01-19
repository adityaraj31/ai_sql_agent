
import pytest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rag import generate_sql, reformulate_question
from src.database import validate_sql_safety

def test_conversational_memory():
    """
    Test 1: Verify that the agent can handle follow-up questions using context.
    """
    print("\n🔹 Test: Conversational Memory")
    
    # Mock history
    history = [
        {"role": "user", "content": "Show me the top 5 customers by sales."},
        {"role": "assistant", "content": "Here they are.", "sql": "SELECT * FROM Customer LIMIT 5"}
    ]
    
    follow_up = "What are their emails?"
    
    # 1. Test Reformulation Logic specifically
    reformulated = reformulate_question(follow_up, history)
    print(f"   Original: {follow_up}")
    print(f"   Reformulated: {reformulated}")
    
    assert "email" in reformulated.lower(), "Reformulated question should ask for emails"
    assert "customer" in reformulated.lower(), "Reformulated question should mention customers"
    
    # 2. Test End-to-End SQL Generation with history
    sql = generate_sql(follow_up, chat_history=history)
    print(f"   Generated SQL: {sql}")
    
    assert "SELECT" in sql.upper()
    assert "Email" in sql, "SQL should select the Email column"
    assert "Customer" in sql, "SQL should query the Customer table"

def test_unrelated_question_refusal():
    """
    Test 2: Verify the agent refuses to answer unrelated questions.
    """
    print("\n🔹 Test: Unrelated Question Refusal")
    question = "What is the capital of France?"
    
    sql = generate_sql(question)
    print(f"   Response SQL: {sql}")
    
    # The prompt instructions say: return `SELECT 'I can only answer questions about the connected database.' AS Service_Message;`
    assert "Service_Message" in sql or "I can only answer" in sql, \
        "Agent should return a polite SQL refusal for unrelated topics."

@pytest.mark.parametrize("query, should_be_safe", [
    ("SELECT * FROM users", True),
    ("WITH cte AS (SELECT 1) SELECT * FROM cte", True),
    ("UPDATE users SET name='Hacked'", False),
    ("DELETE FROM users", False),
    ("DROP TABLE users", False),
    ("SELECT * FROM users; DROP TABLE users", False),
    ("SELECT * FROM users; UPDATE users SET name='x'", False),
    ("EXPLAIN QUERY PLAN SELECT 1", True),
    ("PRAGMA table_info(users)", True),
    ("INSERT INTO users VALUES (1, 'test')", False),
    ("  SELECT * FROM users  ", True),
    ("  select * from users  ", True),
    ("  Delete from users", False),
])
def test_sql_safety_injection(query, should_be_safe):
    """
    Test 3: Verify that destructive commands are caught.
    """
    print(f"\n🔹 Testing Safety: {query}")
    
    error = validate_sql_safety(query)
    is_safe = error is None
    
    assert is_safe == should_be_safe, f"Expected safe={should_be_safe}, but got safe={is_safe}. Error: {error}"

def test_ambiguous_question_handling():
    """
    Test 4: Verify agent makes reasonable assumptions for ambiguous questions.
    """
    print("\n🔹 Test: Ambiguous Question")
    question = "Show me the top albums." 
    # Ambiguous because "top" could mean sales, count, etc.
    # The prompt instructions say: assume "Total Sales" or "Count".
    
    sql = generate_sql(question)
    print(f"   Generated SQL: {sql}")
    
    assert "ORDER BY" in sql.upper(), "Result should be ordered to show 'top' items"
    assert "LIMIT" in sql.upper(), "Result should use LIMIT for 'top' items"

if __name__ == "__main__":
    # Manually run if executed as script
    try:
        test_conversational_memory()
        test_unrelated_question_refusal()
        test_sql_safety_injection()
        test_ambiguous_question_handling()
        print("\n✅ All Edge Cases Passed!")
    except AssertionError as e:
        print(f"\n❌ Test Failed: {e}")
