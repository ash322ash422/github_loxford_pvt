# app.py

import streamlit as st
from step_2_agent_logic import build_agent


# PAGE CONFIG
st.set_page_config(
    page_title="AI Agent with Tools",
    layout="wide"
)

st.title("🤖 AI Agent with Tools")


# SIDEBAR
st.sidebar.header("Settings")

api_key = st.sidebar.text_input(
    "OpenAI API Key",
    type="password"
)

if st.sidebar.button("Quit App"):
    st.warning("App stopped. Refresh the page to restart.")
    st.stop()


# SESSION STATE
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = None

if "current_key" not in st.session_state:
    st.session_state.current_key = None


# BUILD AGENT WHEN API KEY CHANGES
if api_key:

    if st.session_state.current_key != api_key:

        try:

            st.session_state.agent = build_agent(api_key)
            st.session_state.current_key = api_key

            st.sidebar.success("Agent initialized")

        except Exception as e:

            st.sidebar.error(
                f"Failed to initialize agent: {e}"
            )


# DISPLAY CHAT HISTORY
for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.write(message["content"])


# CHAT INPUT
user_input = st.chat_input("Ask something...")

# PROCESS USER INPUT
if user_input:

    if not api_key:
        st.error("Please enter your OpenAI API Key in the sidebar.")

    elif st.session_state.agent is None:
        st.error("Agent is not initialized." )

    else:
        # Show user message
        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_input
            }
        )

        with st.chat_message("user"):
            st.write(user_input)

        # Assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = st.session_state.agent.invoke(
                        {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": user_input
                                }
                            ]
                        }
                    )

                    # Modern LangChain create_agent()
                    answer = response["messages"][-1].content
                    st.write(answer)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer
                        }
                    )

                except Exception as e:
                    error_msg = f"Error: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": error_msg
                        }
                    )