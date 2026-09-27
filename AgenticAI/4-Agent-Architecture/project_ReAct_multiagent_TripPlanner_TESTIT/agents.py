"""
agents.py
=========

All agent logic for the Multi-Agent ReAct Trip Planner, kept separate from
the Streamlit UI so the pattern is easy to read and reuse elsewhere
(CLI, API, tests, etc.).

Contains:
- REACT_PROMPT           : the shared ReAct prompt template (Thought/Action/Observation)
- build_agent()           : builds one ReAct AgentExecutor for a given role
- run_specialist_agent()  : runs one specialist agent and returns its output + trace
- run_writer_agent()      : plain LLM call (no tools) that synthesizes all findings
- plan_trip()             : the Supervisor function that orchestrates all four agents
- SPECIALIST_ROLES        : role definitions for Research / Budget / Logistics agents
"""

from dataclasses import dataclass, field

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_openai import ChatOpenAI


# --------------------------------------------------------------------------
# Shared ReAct prompt template
# --------------------------------------------------------------------------
REACT_PROMPT = PromptTemplate.from_template(
    """You are {role_name}. {role_description}

You have access to the following tools:

{tools}

Use the following format exactly:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation cycle can repeat)
Thought: I now know the final answer
Final Answer: the final answer to the original question, focused only on
your area of expertise ({role_focus}). Be concise and use bullet points.

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
)


# --------------------------------------------------------------------------
# Role definitions for the three specialist agents
# --------------------------------------------------------------------------
@dataclass
class AgentRole:
    key: str
    display_name: str
    description: str
    focus: str


SPECIALIST_ROLES = [
    AgentRole(
        key="research",
        display_name="🔎 Research Agent",
        description=(
            "A travel research specialist who finds current, real attractions, "
            "seasonal events, and typical weather for a destination."
        ),
        focus="attractions, seasonal events, and weather",
    ),
    AgentRole(
        key="budget",
        display_name="💰 Budget Agent",
        description=(
            "A travel budgeting specialist who finds realistic current cost "
            "ranges for flights, hotels, food, and local transport, and builds "
            "a rough total budget estimate."
        ),
        focus="cost estimates and a rough total budget",
    ),
    AgentRole(
        key="logistics",
        display_name="🧳 Logistics Agent",
        description=(
            "A travel logistics specialist who finds current transit options, "
            "visa/entry requirements, and typical opening hours for key sites."
        ),
        focus="transit, visas/entry requirements, and opening hours",
    ),
]


@dataclass
class SpecialistResult:
    role: AgentRole
    output: str
    intermediate_steps: list = field(default_factory=list)


# --------------------------------------------------------------------------
# Agent construction
# --------------------------------------------------------------------------
def get_llm(model_name: str, openai_api_key: str, temperature: float = 0) -> ChatOpenAI:
    """Create the shared chat model used by every agent."""
    return ChatOpenAI(model=model_name, api_key=openai_api_key, temperature=temperature)


def get_tools(tavily_api_key: str, max_results: int = 5):
    """Create the tool list shared by every specialist agent. Tavily only —
    one good search tool is enough to teach the ReAct pattern clearly."""
    return [TavilySearchResults(max_results=max_results, tavily_api_key=tavily_api_key)]


def build_agent(role: AgentRole, llm: ChatOpenAI, tools: list) -> AgentExecutor:
    """Build a ReAct AgentExecutor for one specialist role."""
    prompt = REACT_PROMPT.partial(
        role_name=role.display_name,
        role_description=role.description,
        role_focus=role.focus,
    )
    agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=6,
        return_intermediate_steps=True,
    )


# --------------------------------------------------------------------------
# Running individual agents
# --------------------------------------------------------------------------
def run_specialist_agent(role: AgentRole, question: str, llm: ChatOpenAI, tools: list) -> SpecialistResult:
    """Run a single specialist ReAct agent and return its output + reasoning trace."""
    executor = build_agent(role, llm, tools)
    result = executor.invoke({"input": question})
    return SpecialistResult(
        role=role,
        output=result["output"],
        intermediate_steps=result["intermediate_steps"],
    )


def run_writer_agent(trip_summary: str, specialist_results: list, llm: ChatOpenAI) -> str:
    """Plain LLM call (no tools) that synthesizes all specialist findings into
    one final itinerary. This agent doesn't need ReAct/tools because its job
    is pure synthesis of information the other agents already gathered."""
    findings_block = "\n\n".join(
        f"--- {r.role.display_name} findings ---\n{r.output}" for r in specialist_results
    )

    prompt = f"""You are a professional travel writer. Combine the following
research from specialist agents into a single, clear, day-by-day itinerary
for this trip:

{trip_summary}

{findings_block}

Write a friendly, well-organized day-by-day itinerary. Include a short budget
summary and any key logistics notes (visas, transit passes, etc.) at the end.
"""
    return llm.invoke(prompt).content


# --------------------------------------------------------------------------
# Supervisor: orchestrates the full multi-agent run
# --------------------------------------------------------------------------
def format_trace(intermediate_steps) -> str:
    """Turn AgentExecutor's intermediate_steps into readable Thought/Action/Observation text."""
    lines = []
    for action, observation in intermediate_steps:
        lines.append(f"**Thought/Action:**\n```\n{action.log.strip()}\n```")
        obs_preview = str(observation)
        if len(obs_preview) > 800:
            obs_preview = obs_preview[:800] + " ... (truncated)"
        lines.append(f"**Observation:**\n```\n{obs_preview}\n```")
    return "\n\n".join(lines) if lines else "_No tool calls were needed._"


def plan_trip(
    trip_summary: str,
    model_name: str,
    openai_api_key: str,
    tavily_api_key: str,
    on_specialist_done=None,
) -> tuple[list, str]:
    """
    The Supervisor function: runs each specialist agent in sequence, then
    the Writer agent, and returns everything needed to display results.

    on_specialist_done: optional callback(SpecialistResult) called right
    after each specialist agent finishes — lets the UI layer stream progress
    (e.g. update Streamlit) without this module knowing anything about Streamlit.

    Returns: (list_of_SpecialistResult, final_itinerary_text)
    """
    llm = get_llm(model_name, openai_api_key)
    tools = get_tools(tavily_api_key)

    specialist_results = []
    for role in SPECIALIST_ROLES:
        question = f"{role.description}\n\nTrip details:\n{trip_summary}"
        result = run_specialist_agent(role, question, llm, tools)
        specialist_results.append(result)
        if on_specialist_done:
            on_specialist_done(result)

    final_itinerary = run_writer_agent(trip_summary, specialist_results, llm)
    return specialist_results, final_itinerary
