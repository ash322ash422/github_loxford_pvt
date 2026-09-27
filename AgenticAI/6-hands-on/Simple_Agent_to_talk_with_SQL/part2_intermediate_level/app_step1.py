import streamlit as st

from config import get_openai_client
from sql_agent import generate_sql
from database import run_query
from guardrails import is_safe_question, is_safe_sql

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="AI SQL Agent",
    layout="wide"
)

# =====================================================
# TITLE
# =====================================================

st.title("AI SQL Business Agent")

st.write("Ask business questions using natural language.")

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Configuration")

api_key = st.sidebar.text_input(
    "Enter OpenAI API Key",
    type="password"
)

# =====================================================
# USER QUESTION
# =====================================================

user_question = st.text_area(
    "Ask a business question"
)

# =====================================================
# BUTTON
# =====================================================

if st.button("Generate Insights"):

    # API KEY CHECK
    if not api_key:

        st.error("Please enter OpenAI API key")
        st.stop()

    # QUESTION SAFETY CHECK
    if not is_safe_question(user_question):

        st.error("This question violates privacy policies.")
        st.stop()

    # CREATE CLIENT
    client = get_openai_client(api_key)

    # GENERATE SQL
    with st.spinner("Generating SQL Query..."):

        sql_query = generate_sql(client, user_question)

    st.subheader("Generated SQL")

    st.code(sql_query, language="sql")

    # SQL SAFETY CHECK
    if not is_safe_sql(sql_query):

        st.error("Unsafe SQL detected.")
        st.stop()

    # RUN QUERY
    with st.spinner("Executing Query..."):

        result = run_query(sql_query)

    # DISPLAY RESULTS
    st.subheader("Query Results")

    st.dataframe(result)