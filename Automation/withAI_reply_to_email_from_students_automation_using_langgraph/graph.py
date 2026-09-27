"""
Wires the individual node functions into a LangGraph StateGraph.

This is the "shape" of the agent. Notice how little logic actually lives
here -- graph.py is just plumbing. All the "thinking" is in nodes/.
"""
from langgraph.graph import StateGraph, START, END

from state import GraphState
from nodes.classify import classify_email
from nodes.extract import extract_student_info
from nodes.policy_decision import apply_policy
from nodes.draft import draft_reply


def _mark_not_relevant(state: GraphState) -> GraphState:
    return {"status": "not a student-assignment email -- skipped, no draft created"}


def _route_after_classification(state: GraphState) -> str:
    """Conditional edge: only extension/late/grade emails proceed to drafting."""
    return "extract" if state["is_relevant"] else "not_relevant"


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("classify", classify_email)
    graph.add_node("extract", extract_student_info)
    graph.add_node("policy_decision", apply_policy)
    graph.add_node("draft", draft_reply)
    graph.add_node("not_relevant", _mark_not_relevant)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        _route_after_classification,
        {"extract": "extract", "not_relevant": "not_relevant"},
    )
    graph.add_edge("extract", "policy_decision")
    graph.add_edge("policy_decision", "draft")
    graph.add_edge("draft", END)
    graph.add_edge("not_relevant", END)

    return graph.compile()


# Build once, reuse across runs
student_email_agent = build_graph()


if __name__ == "__main__":
    try:
        # Generate the PNG binary data from the compiled graph
        png_data = student_email_agent.get_graph().draw_mermaid_png()
        
        # Save the binary data to a file
        output_filename = "graph.png"
        with open(output_filename, "wb") as f:
            f.write(png_data)
            
        print(f"Successfully saved graph visualization to: {output_filename}")
        
    except Exception as e:
        print(f"Failed to save graph image: {e}")
        print("Tip: Ensure you have 'pygraphviz' or 'grandalf' installed if using local rendering,")
        print("or that you have an active internet connection for the remote Mermaid API fallback.")
