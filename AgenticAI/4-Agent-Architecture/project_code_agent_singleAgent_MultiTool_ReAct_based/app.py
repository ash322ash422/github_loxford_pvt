import streamlit as st
from agent import create_code_agent


st.set_page_config(page_title="Code Generation & Execution Agent", layout="wide")

EXAMPLE_PROMPTS = [
    "Generate a Python function for addition, then execute it with the \
        inputs 5 and 7. Show me the code and tell me the result.",
        
    "Generate a Python script that calculates the first 10 Fibonacci numbers, \
        then execute it and show me the code and result.",
        
    "Create a script in python to calculate value of PI upto 4 decimals using random numbers.\
        Execute this and show me the result",
        
    "Write a Python function that checks if a number is prime, then run it on the \
        numbers 7, 10, and 13 and tell me the results.",
]

# --- Session state setup ---
if "history" not in st.session_state:
    st.session_state.history = []

if "task_input" not in st.session_state:
    st.session_state.task_input = ""

if "agent" not in st.session_state:
    st.session_state.agent = None

if "agent_key" not in st.session_state:
    st.session_state.agent_key = None


# --- Sidebar ---
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("OpenAI API key", type="password", help="Your key is kept only in this session.")

    st.divider()
    st.header("Example prompts")
    st.caption("Click an example to load it into the task box.")
    for example in EXAMPLE_PROMPTS:
        if st.button(example, use_container_width=True, key=f"example_{example}"):
            st.session_state.task_input = example
            st.rerun()


# --- Main area ---
st.title("Code Generation & Execution Agent")

task = st.text_area("Enter your coding task", height=120, key="task_input")

run_clicked = st.button("Run", type="primary")

if run_clicked:
    if not api_key:
        st.error("Please enter your OpenAI API key in the sidebar.")
    elif not task.strip():
        st.warning("Please enter a task.")
    else:
        # Recreate the agent only if the API key has changed (cheap, but avoids needless recreation)
        if st.session_state.agent is None or st.session_state.agent_key != api_key:
            st.session_state.agent = create_code_agent(api_key=api_key)
            st.session_state.agent_key = api_key

        with st.spinner("Agent is working..."):
            try:
                response = st.session_state.agent.invoke(
                    {"messages": [{"role": "user", "content": task}]}
                )
                result = response["messages"][-1].content
                st.session_state.history.insert(0, {"task": task, "result": result})
            except Exception as e:
                st.error(f"Error: {e}")


# --- Results / history ---
if st.session_state.history:
    st.subheader("Results")
    for i, item in enumerate(st.session_state.history):
        with st.expander(item["task"], expanded=(i == 0)):
            st.markdown(item["result"])
else:
    st.info("Enter a task above (or pick an example from the sidebar) and click Run.")