# STEP 1 IMPORT LIBRARIES

import sqlite3
import pandas as pd
from openai import OpenAI
import os
from dotenv import load_dotenv

# STEP 2 OPENAI CLIENT
load_dotenv() # Load variables from .env
open_api_key = os.getenv("OPEN_AI_API_KEY") # Access them
client = OpenAI(api_key=open_api_key)

# STEP 3 CONNECT TO DATABASE
# Replace with your database file
conn = sqlite3.connect("business.db")


# STEP 4: DATABASE SCHEMA

schema = """

TABLE: Customers
--------------------------------
customer_id INT PRIMARY KEY
name VARCHAR(100)
city VARCHAR(100)


TABLE: Orders
--------------------------------
order_id INT PRIMARY KEY
customer_id INT
amount DECIMAL(10,2)
order_date DATE
item VARCHAR(100)

Relationship:
Orders.customer_id references Customers.customer_id


TABLE: Shippings
--------------------------------
ship_id INT PRIMARY KEY
order_id INT
status VARCHAR(50)

Relationship:
Shippings.order_id references Orders.order_id

"""

# STEP 5: FUNCTION TO GENERATE SQL:
# This function takes user question as input, constructs a prompt for the LLM, and 
# returns the generated SQL query.

def generate_sql(user_question):

    prompt = f"""
    You are an expert SQL assistant.

    Your task is to convert natural language into SQL queries.

    DATABASE SCHEMA:
    {schema}

    IMPORTANT RULES:
    1. ONLY return SQL query
    2. DO NOT explain anything
    3. Use SQLite syntax
    4. Use JOINs whenever needed
    5. Use table names exactly as given
    6. Never generate INSERT, UPDATE, DELETE, DROP
    7. Only generate SELECT statements

    USER QUESTION:
    {user_question}
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "You generate SQL SELECT queries only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )
    
    # print("DEBUG: response: ", response)
    sql_query = response.choices[0].message.content.strip()

    # Remove markdown formatting if model adds it
    sql_query = sql_query.replace("```sql", "")
    sql_query = sql_query.replace("```", "")
    sql_query = sql_query.strip()

    return sql_query

# STEP 6: EXECUTE SQL SAFELY

def execute_sql(sql_query):

    try:

        # Safety check
        allowed = sql_query.lower().startswith("select")

        if not allowed:
            print("\nONLY SELECT STATEMENTS ALLOWED")
            return None

        df = pd.read_sql_query(sql_query, conn)

        return df

    except Exception as e:

        print("\nSQL EXECUTION ERROR:")
        print(e)

        return None

# STEP 7: ASK USER QUESTION

user_question = input("\nAsk a business question: ")

# STEP 8: GENERATE SQL

generated_sql = generate_sql(user_question)

print("\n" + "="*50)
print("GENERATED SQL")
print("="*50)

print(generated_sql)

# STEP 9: EXECUTE QUERY

result_df = execute_sql(generated_sql)

# STEP 10: DISPLAY RESULTS

if result_df is not None:

    print("\n" + "="*50)
    print("QUERY RESULTS")
    print("="*50)

    print(result_df)

# =========================================================
# SAMPLE QUESTIONS FOR CLASS DEMO
# =========================================================

"""
1. Show all customers from Chicago

2. Show customers who ordered 'Phone'

3. Which customer spent the most money?

4. Show total sales by city

5. Which item generated highest revenue?

6. Show all delivered orders

7. Show all shipped orders with customer names

8. Which city has highest sales?

9. Show average order amount by city

10. Show customers with more than one order

11. Show all pending shipments

12. Show total revenue generated

13. Show all Computer orders

14. Which customers never placed an order?

15. Show all orders with shipping status
"""


# Sample output for question: "Show all customers from Chicago ?"
"""
Ask a business question: Show all customers from Chicago

==================================================
GENERATED SQL
==================================================
SELECT * FROM Customers WHERE city = 'Chicago';

==================================================
QUERY RESULTS
==================================================
   customer_id     name     city
0            3   Mozart  Chicago
1            6  Fischer  Chicago
"""

# Sample output for question: Show customers who ordered 'Phone'
"""
Ask a business question: Show customers who ordered 'Phone'

==================================================
GENERATED SQL
==================================================
SELECT DISTINCT Customers.*
FROM Customers
JOIN Orders ON Customers.customer_id = Orders.customer_id
WHERE Orders.item = 'Phone';

==================================================
QUERY RESULTS
==================================================
   customer_id     name         city
0            1   Wagner     New York
1            3   Mozart      Chicago
2            6  Fischer      Chicago
3            2  Shankar  Los Angeles    
"""


# Sample output for question: Which customer spent the most money?
"""
Ask a business question: Which customer spent the most money?

==================================================
GENERATED SQL
==================================================
SELECT c.customer_id, c.name, c.city, SUM(o.amount) AS total_spent
FROM Customers c
JOIN Orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name, c.city
ORDER BY total_spent DESC
LIMIT 1;

==================================================
QUERY RESULTS
==================================================
   customer_id     name         city  total_spent
0            2  Shankar  Los Angeles          400
"""