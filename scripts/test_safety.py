import sys
import os

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database import validate_sql_safety

def test_safety():
    test_cases = [
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
    ]

    failed = 0
    for query, expected_safe in test_cases:
        result = validate_sql_safety(query)
        is_safe = result is None
        
        if is_safe != expected_safe:
            print(f"FAILED: Query: {query}")
            print(f"  Expected Safe: {expected_safe}, Got: {is_safe}")
            if not is_safe:
                print(f"  Error: {result}")
            failed += 1
        else:
            print(f"PASSED: {query[:30]}... -> {'Safe' if is_safe else 'Unsafe'}")

    if failed == 0:
        print("\nAll safety tests passed!")
    else:
        print(f"\n{failed} tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    test_safety()
