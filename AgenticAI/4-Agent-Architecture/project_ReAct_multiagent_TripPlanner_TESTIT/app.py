"""
app.py
======

Streamlit UI for the Multi-Agent ReAct Trip Planner.

All agent/LLM logic lives in agents.py — this file only handles:
- Sidebar API key inputs
- The trip-request form
- Displaying each agent's output and reasoning trace as they complete

Run with:
    streamlit run app.py

Requirements:
    pip install streamlit langchain langchain-openai langchain-community tavily-python
"""

import streamlit as st

from agents import plan_trip, format_trace

# --------------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------------
st.set_page_config(page_title="Multi-Agent ReAct Trip Planner", page_icon="🧭", layout="wide")
st.title("🧭 Multi-Agent ReAct Trip Planner")
st.caption(
    "A teaching demo: a Supervisor delegates to specialist ReAct agents "
    "(Research, Budget, Logistics) that use Tavily web search, then a "
    "Writer agent synthesizes their findings into one itinerary."
)

# --------------------------------------------------------------------------
# Sidebar: API keys & settings
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("🔑 API Keys")
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    tavily_api_key = st.text_input("Tavily API Key", type="password")

    st.divider()
    st.header("⚙️ Settings")
    model_name = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"], index=0)
    show_traces = st.checkbox("Show agent reasoning traces (Thought/Action/Observation)", value=True)

    st.divider()
    st.markdown(
        "**Get keys:**\n"
        "- OpenAI: platform.openai.com\n"
        "- Tavily: tavily.com (free tier available)"
    )

keys_ready = bool(openai_api_key) and bool(tavily_api_key)

# --------------------------------------------------------------------------
# Main input form
# --------------------------------------------------------------------------
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    destination = st.text_input("Destination", placeholder="e.g. Kyoto, Japan")
with col2:
    duration = st.text_input("Trip length", placeholder="e.g. 4 days")
with col3:
    travel_dates = st.text_input("Travel dates / season", placeholder="e.g. mid-November")

budget_level = st.select_slider(
    "Budget level", options=["Backpacker", "Mid-range", "Luxury"], value="Mid-range"
)
extra_notes = st.text_area(
    "Anything else the agents should know?",
    placeholder="e.g. traveling with kids, interested in food and temples, no hiking",
)

run_button = st.button("🚀 Plan My Trip", type="primary", disabled=not keys_ready)

if not keys_ready:
    st.info("Enter your OpenAI and Tavily API keys in the sidebar to get started.")

# --------------------------------------------------------------------------
# Run the multi-agent pipeline (Supervisor lives in agents.py)
# --------------------------------------------------------------------------
if run_button and keys_ready:
    if not destination:
        st.warning("Please enter a destination.")
        st.stop()

    trip_summary = (
        f"Destination: {destination}\n"
        f"Trip length: {duration or 'not specified'}\n"
        f"Travel dates/season: {travel_dates or 'not specified'}\n"
        f"Budget level: {budget_level}\n"
        f"Additional notes: {extra_notes or 'none'}"
    )

    st.divider()
    st.header("🧠 Specialist Agents at Work")
    results_container = st.container()

    # This callback lets agents.py stay UI-agnostic: it just calls this
    # function after each specialist agent finishes, and we decide how to
    # render that in Streamlit.
    def on_specialist_done(result):
        with results_container:
            st.subheader(result.role.display_name)
            if show_traces:
                with st.expander("🔍 Show ReAct reasoning trace", expanded=False):
                    st.markdown(format_trace(result.intermediate_steps))
            st.markdown(result.output)

    with st.spinner("Specialist agents are researching your trip..."):
        specialist_results, final_itinerary = plan_trip(
            trip_summary=trip_summary,
            model_name=model_name,
            openai_api_key=openai_api_key,
            tavily_api_key=tavily_api_key,
            on_specialist_done=on_specialist_done,
        )

    st.divider()
    st.header("✍️ Writer Agent — Final Itinerary")
    st.markdown(final_itinerary)

    st.divider()
    st.caption(
        "💡 Teaching note: each specialist agent above ran its own independent "
        "ReAct loop (deciding when/what to search and when it had enough "
        "information), while plan_trip() in agents.py acted as the Supervisor "
        "— a simple sequential multi-agent pattern. Try swapping this for a "
        "framework like LangGraph to see the same pattern with explicit "
        "agent-to-agent message passing."
    )
