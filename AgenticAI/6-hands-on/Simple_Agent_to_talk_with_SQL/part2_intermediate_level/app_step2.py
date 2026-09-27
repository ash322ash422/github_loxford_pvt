import streamlit as st
import pandas as pd

from config import get_openai_client
from sql_agent import generate_sql
from database import run_query
from guardrails import is_safe_question, is_safe_sql

# PAGE CONFIG

st.set_page_config(
    page_title="AI SQL Agent",
    layout="wide"
)

# SESSION STATE
if "history" not in st.session_state:
    st.session_state.history = []

if "quit_app" not in st.session_state:
    st.session_state.quit_app = False

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

st.sidebar.markdown("---")

# QUIT BUTTON
if st.sidebar.button("Quit Application"):
    st.session_state.quit_app = True

# STOP APP IF QUIT PRESSED
if st.session_state.quit_app:
    st.warning("Application stopped. Refresh browser to restart.")
    st.stop()

# =====================================================
# CLEAR HISTORY BUTTON
# =====================================================

if st.sidebar.button("Clear History"):

    st.session_state.history = []

# =====================================================
# USER QUESTION
# =====================================================

user_question = st.text_area(
    "Ask a business question",
    height=120
)

# =====================================================
# GENERATE BUTTON
# =====================================================

if st.button("Generate Insights"):

    # API KEY CHECK
    if not api_key:

        st.error("Please enter OpenAI API key")
        st.stop()

    # EMPTY QUESTION CHECK
    if not user_question.strip():

        st.warning("Please enter a question.")
        st.stop()

    # QUESTION SAFETY CHECK
    if not is_safe_question(user_question):

        st.error("This question violates privacy policies.")
        st.stop()

    # CREATE OPENAI CLIENT
    client = get_openai_client(api_key)

    # GENERATE SQL
    with st.spinner("Generating SQL Query..."):
        sql_query = generate_sql(client, user_question)

    # SHOW SQL
    st.subheader("Generated SQL")
    st.code(sql_query, language="sql")

    
    # SQL SAFETY CHECK
    if not is_safe_sql(sql_query):
        st.error("Unsafe SQL detected.")
        st.stop()

    # EXECUTE QUERY

    with st.spinner("Executing Query..."):
        result = run_query(sql_query)

    # STORE HISTORY
    st.session_state.history.append({
        "question": user_question,
        "sql": sql_query,
        "result": result
    })

# DISPLAY HISTORY
if st.session_state.history:
    st.markdown("---")
    st.header("Query History")
    
    for i, item in enumerate(reversed(st.session_state.history), start=1):
        with st.expander(f"Query {i}: {item['question']}"):
            st.code(item["sql"], language="sql")
            
            # SHOW NUMBER OF ROWS
            st.write(f"Rows Returned: {len(item['result'])}")

            # DISPLAY DATAFRAME
            st.dataframe(
                item["result"],
                height=250,
                use_container_width=False
            )

            # DOWNLOAD BUTTON
            csv = item["result"].to_csv(index=False)

            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="query_results.csv",
                mime="text/csv",
                key=f"download_{i}"
            )