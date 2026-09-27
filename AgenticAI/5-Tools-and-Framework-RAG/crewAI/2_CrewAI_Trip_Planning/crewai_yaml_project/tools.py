from crewai.tools import tool
from ddgs import DDGS


@tool("Web Search Tool")
def web_search(query: str) -> str:
    """Search the web for up-to-date information. Input should be a search query string.
    Returns the top results as a short list of title, snippet, and link."""
    results = DDGS().text(query, max_results=5)
    if not results:
        return f"No results found for '{query}'."
    lines = [f"- {r['title']}: {r['body']} ({r['href']})" for r in results]
    return "\n".join(lines)
