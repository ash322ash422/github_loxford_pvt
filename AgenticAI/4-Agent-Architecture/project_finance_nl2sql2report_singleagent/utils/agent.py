"""
utils/agent.py
LangGraph pipeline: NL question → SQL → execute → summarize.

Graph nodes
───────────
generate_sql   : LLM converts the user question to a SQL query
execute_sql    : Run the query against SQLite
summarise      : LLM writes a plain-English summary of the results
"""

import re
import pandas as pd
from typing import TypedDict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from utils.db import get_schema, run_query

# Shared state flowing through the graph 
class AgentState(TypedDict):
    question:  str
    sql:       Optional[str]
    df:        Optional[pd.DataFrame]
    summary:   Optional[str]
    error:     Optional[str]


# LLM (swap model or add temperature as needed) 
def get_llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


# Node 1: Generate SQL 
def generate_sql(state: AgentState) -> AgentState:
    schema  = get_schema()
    llm     = get_llm()

    system = f"""You are an expert SQL assistant for a bank lending SQLite database.

            Database schema:
            {schema}

            Rules:
            - Output ONLY the raw SQL query — no markdown, no backticks, no explanation.
            - Use only SELECT statements (read-only).
            - Use table and column names exactly as shown in the schema.
            - Prefer readable aliases (e.g. COUNT(*) AS total_loans).
            - Limit results to 500 rows unless the question implies otherwise.
    """
    
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=state["question"]),
    ]

    response = llm.invoke(messages)
    sql = response.content.strip()

    # Strip accidental markdown fences
    sql = re.sub(r"^```(?:sql)?", "", sql, flags=re.IGNORECASE).strip()
    sql = re.sub(r"```$", "", sql).strip()

    return {**state, "sql": sql, "error": None}


# Node 2: Execute SQL 

def execute_sql(state: AgentState) -> AgentState:
    if state.get("error"):
        return state
    try:
        df = run_query(state["sql"])
        return {**state, "df": df}
    except Exception as e:
        return {**state, "df": None, "error": str(e)}


# Node 3: Summarise results

def summarise(state: AgentState) -> AgentState:
    if state.get("error"):
        return {**state, "summary": f"⚠️ Could not run query: {state['error']}"}

    df  = state["df"]
    llm = get_llm()

    preview = df.head(10).to_string(index=False) if df is not None else "No data."

    system = """
    You are a concise data analyst. 
    Summarise the query result in 2-4 plain-English sentences. 
    Highlight key numbers and trends.
    """
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=f"Question: {state['question']}\n\nData preview:\n{preview}"),
    ]
    
    response = llm.invoke(messages)
    return {**state, "summary": response.content.strip()}


# Build the LangGraph

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("generate_sql", generate_sql)
    graph.add_node("execute_sql",  execute_sql)
    graph.add_node("summarise",    summarise)

    graph.set_entry_point("generate_sql")
    graph.add_edge("generate_sql", "execute_sql")
    graph.add_edge("execute_sql",  "summarise")
    graph.add_edge("summarise",    END)

    return graph.compile()


# ── Public entry point

def run_agent(question: str) -> AgentState:
    app   = build_graph()
    state = AgentState(question=question,
                       sql=None,
                       df=None,
                       summary=None,
                       error=None
    )
    
    return app.invoke(state)
