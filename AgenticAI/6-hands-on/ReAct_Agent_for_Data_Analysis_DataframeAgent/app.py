import streamlit as st
import pandas as pd

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from tools import dataframe_tool_factory

# -------------------------
# STREAMLIT UI
# -------------------------
st.set_page_config(page_title="Data Agent App", layout="wide")
st.title("📊 LLM-Powered Data Analysis")

# -------------------------
# SIDEBAR (API KEY)
# -------------------------
st.sidebar.header("Settings")

api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")

if not api_key:
    st.warning("Please enter your OpenAI API key in the sidebar")
    st.stop()

# -------------------------
# INITIALIZE LLM
# -------------------------
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=api_key,
    temperature=0
)

# -------------------------
# FILE UPLOAD
# -------------------------
uploaded_file = st.file_uploader("Upload CSV", type=["csv","xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.write("### Data Preview:")
        st.dataframe(df.head())

        tool = dataframe_tool_factory(df)
        
        agent = create_agent(
            model=llm,
            tools=[tool],
            system_prompt="""
                You are a data analyst.

                A pandas dataframe named df is available.

                Use the dataframe_python tool whenever you need
                to inspect, calculate, aggregate, filter, or analyze data.

                Never guess values.
                Always use the tool.
            """
        )

        # -------------------------
        # USER QUERY
        # -------------------------
        user_query = st.text_input("Ask a question about your data:")

        if user_query:
            
            with st.spinner("Analyzing your data..."):
                result = agent.invoke(
                    { "messages":   [{"role": "user",
                                     "content": user_query 
                                    }] 
                    }
                )

            
            messages = result["messages"]
            final_answer = messages[-1].content
            st.subheader("Final Answer")
            st.success(final_answer)
            
            st.subheader("Tools Used")
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        st.write( f"Tool: {tool_call['name']}" )
                        st.code( tool_call["args"]["code"], language="python" )
            
    except Exception as e:
        st.error(f"Error: {e}")
