# MarketIntel MCP classroom demo

MarketIntel is a local MCP server for market research. Its tools can look up company profiles, competitors, product portfolios, pricing, and recent news using Tavily. The server also exposes a topic list as an MCP **resource**, a reusable competitor brief template as an MCP **prompt**, and a connection test called `server_identity`.

Both clients connect to the same server over SSE at `http://127.0.0.1:8000/sse`. The difference is who chooses the tool.

| File | What it does |
|---|---|
| `server.py` | Publishes the MCP components and calls Tavily when a research tool runs. |
| `client_1_no_llm.py` | Python chooses the tool from command-line arguments. The client displays the Tavily answer and source links. With no arguments, it inspects the MCP server without a search. |
| `client_2_with_LLM.py` | Takes a natural-language question. Gemini chooses whether to request a tool and supplies its arguments. LangChain calls the tool through MCP and passes the result back to Gemini to write the answer. |

## 1. Set up in PowerShell

Use Python 3.11 or later. Open PowerShell in the `marketintel_mcp_demo` folder. If a virtual environment already exists there, reuse it and skip the first command.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install "langchain==1.3.6" "langchain-google-genai==4.4.0" "langchain-mcp-adapters==0.3.2"
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
notepad .env
```

Add the keys to `.env`. The last install command is only needed for the Gemini client.

```dotenv
TAVILY_API_KEY=your_tavily_key
GEMINI_API_KEY=your_gemini_key
```

- [Tavily key](https://app.tavily.com/) — used by the server for live research. The first client's inspection command works without either key.
- [Gemini key](https://aistudio.google.com/apikey) — used by the second client. If neither `GOOGLE_API_KEY` nor `GEMINI_API_KEY` is set, the client prompts for a key. It checks `GOOGLE_API_KEY` first.

## 2. Start the server in Terminal 1

```powershell
.\.venv\Scripts\python.exe server.py
```

Leave this terminal open while running either client. The server should show `http://127.0.0.1:8000/sse`.

## 3. Run the client without an LLM in Terminal 2

Open a second PowerShell terminal in the same folder. Run these one at a time.

```powershell
.\.venv\Scripts\python.exe client_1_no_llm.py
.\.venv\Scripts\python.exe client_1_no_llm.py "Zoho" --region India
.\.venv\Scripts\python.exe client_1_no_llm.py "Zoho" --region India --competitors
```

1. The first command calls `server_identity`, lists six tools, reads the market topics resource, and renders the competitor prompt as text.
2. The second command calls `company_overview` and prints the Tavily query, answer, and up to three source links.
3. The third command uses `--competitors` to select `list_competitors`. Add `--json` to a search command to see the full tool response.

## 4. Run the Gemini client in Terminal 2

Keep the same server running.

```powershell
.\.venv\Scripts\python.exe client_2_with_LLM.py "Who are Zoho's main CRM competitors in India? Cite your sources."
.\.venv\Scripts\python.exe client_2_with_LLM.py "What is a CRM?"
```

The first question should lead Gemini to request `list_competitors`. The second can be answered directly. Compare the **Tool requests** section in both runs. You can also run the script without a question to get an interactive prompt for one question.

## 30-minute classroom plan

| Time | Activity |
|---|---|
| 0–5 min | Start the server and point out the tool, resource, and prompt decorators. |
| 5–12 min | Run the first client without arguments. Show the identity response, tool list, topic list, and rendered prompt. |
| 12–20 min | Run the first client's competitors command. Trace the command-line arguments into the Tavily query and open one source. |
| 20–30 min | Ask both Gemini questions. Compare which tools Gemini requests with the tool Python selected in the previous step. |

## Troubleshooting

- **Connection refused** — Check that Terminal 1 is still running. If you change port 8000, update the port in the server and both client URLs.
- **Tavily key or search error** — Check `TAVILY_API_KEY` and restart the server after editing `.env`. You can still run the first client's inspection command.
- **Gemini key or model error** — Check the Gemini key. The client uses `gemini-3.5-flash` by default. Set `GEMINI_MODEL` in `.env` if you need to use a different Gemini model with tool calling.

Stop the server with **Ctrl+C** in Terminal 1.

