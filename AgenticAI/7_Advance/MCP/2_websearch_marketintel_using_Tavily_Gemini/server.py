"""MarketIntel MCP server for a local classroom demonstration."""

import os
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP
from tavily import TavilyClient

load_dotenv(Path(__file__).with_name(".env"))
mcp = FastMCP(name="MarketIntel")


def _tavily_client() -> TavilyClient:
    """Create a Tavily client only when a search tool needs it."""
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key or api_key == "paste_your_tavily_key_here":
        raise ValueError("Set TAVILY_API_KEY in the .env file beside server.py.")
    return TavilyClient(api_key=api_key)


def _tsearch(query: str, max_results: int, **options) -> dict:
    """Search Tavily and keep the answer, query, and source details."""
    response = _tavily_client().search(
        query=query,
        max_results=max_results,
        search_depth="advanced",
        include_answer="advanced",
        **options,
    )
    return {
        "query_used": query,
        "answer": response.get("answer"),
        "results": [
            {key: item.get(key) for key in ("title", "url", "content", "score", "published_date")}
            for item in response.get("results", [])
        ],
    }


@mcp.resource("resource://market/topics")
def market_topics() -> list[str]:
    """Return a static list of topics for market research."""
    return [
        "Competitor overview", "Pricing snapshot", "Product portfolio mapping",
        "Market landscape", "Feature comparison", "Regional GTM",
    ]


@mcp.tool(annotations={"title": "Company Overview"})
def company_overview(name: str, region: str | None = None, max_results: int = 8) -> dict:
    """Search for a company's background, products, business model, and news."""
    reg = f" in {region}" if region else ""
    query = f"Company overview of {name}{reg}: founding, HQ, products, business model, recent news"
    return _tsearch(query, max_results)


@mcp.tool(annotations={"title": "List Competitors"})
def list_competitors(
    name: str, category: str | None = None, region: str | None = None, max_results: int = 10
) -> dict:
    """Search for competitors in an optional category and region."""
    cat = f" in {category}" if category else ""
    reg = f" in {region}" if region else ""
    query = f"Top competitors of {name}{cat}{reg}; include upstart challengers"
    return _tsearch(query, max_results)


@mcp.tool(annotations={"title": "Product Portfolio Map"})
def product_portfolio(
    company: str, focus_keywords: list[str] | None = None, max_results: int = 12
) -> dict:
    """Search for products and extract text from likely product pages."""
    keywords = f" ({', '.join(focus_keywords)})" if focus_keywords else ""
    query = f"{company} product portfolio{keywords}: product list, suites, tiers, segments"
    search_result = _tsearch(query, max_results)
    product_urls = [
        result["url"] for result in search_result["results"]
        if result.get("url")
        and any(term in result["url"].lower() for term in ("product", "pricing", "solutions"))
    ]

    extracted = {}
    if product_urls:
        try:
            extracted = _tavily_client().extract(
                urls=product_urls[:10], extract_depth="advanced", format="markdown"
            )
        except Exception as error:
            extracted = {"error": f"extract_failed: {error}"}
    return {"search": search_result, "extracted": extracted}


@mcp.tool(annotations={"title": "Pricing Snapshot"})
def pricing_snapshot(
    product_or_company: str, region: str | None = None,
    currency_hint: str | None = None, max_results: int = 10,
) -> dict:
    """Search for pricing tiers, billing cycles, and discounts."""
    reg = f" in {region}" if region else ""
    currency = f" in {currency_hint}" if currency_hint else ""
    query = f"Pricing for {product_or_company}{reg}{currency}: list price, tiers, billing cycles, discounts, hidden fees"
    return _tsearch(query, max_results)


@mcp.tool(annotations={"title": "Recent News Pulse"})
def recent_news_pulse(company: str, days: int = 30, max_results: int = 10) -> dict:
    """Search for company news published since the requested cutoff date."""
    if days < 1:
        raise ValueError("days must be at least 1.")
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    query = f"Recent news about {company}: funding, acquisitions, launches, leadership"
    return _tsearch(query, max_results, topic="news", start_date=cutoff)


@mcp.prompt
def competitor_analysis_prompt(company: str, region: str = "", category: str = "") -> str:
    """Fill in a reusable competitor brief prompt."""
    return (
        f"Build a competitor brief for '{company}'"
        + (f" in '{region}'" if region else "")
        + (f" within '{category}'" if category else "")
        + ". Steps: 1) Company Overview 2) List Competitors 3) Portfolio & Pricing 4) News Pulse 5) SWOT+Five Forces."
    )


@mcp.tool
def server_identity() -> dict:
    """Identify the running server without calling Tavily."""
    return {
        "server": "MarketIntel",
        "file": str(Path(__file__).resolve()),
        "build": "marketintel-test-001",
    }


def main() -> None:
    """Run the local SSE server on port 8000."""
    print("MarketIntel MCP endpoint: http://127.0.0.1:8000/sse", flush=True)
    mcp.run(transport="sse", host="127.0.0.1", port=8000, show_banner=False)


if __name__ == "__main__":
    main()

