# LangSmith for beginners — 35-minute lesson

Start with `01_langsmith_essentials.ipynb`. It explains what LangSmith is, why it helps, and what the lesson covers. Each example includes its purpose and expected result. Allow up to 40 minutes for teaching, excluding account setup and installation.

From this directory, using Python 3.11+:

```text
python -m pip install -r requirements.txt
python -m jupyterlab 01_langsmith_essentials.ipynb
```

The default local walkthrough uses a deterministic keyword demo and no network calls after installation. This is not an offline LangSmith service. To see actual hosted traces and experiments, copy `.env.example` to `.env`, set your LangSmith key and destination, and change `ENABLE_LANGSMITH=True` in the notebook. You can keep `USE_DEMO_MODEL=True` to teach the hosted platform without provider calls.

For real generation, install the selected provider SDK using the notebook's install instructions (or install all with `python -m pip install -r requirements-providers.txt`). Set `PROVIDER` to `gemini`, `openai`, or `huggingface`, supply its key and an available model ID in `.env`, and set `USE_DEMO_MODEL=False`. Restart and run top to bottom after switching providers. Hugging Face uses hosted inference. A standard pass makes nine model calls; they may incur charges. Hosted mode uploads the synthetic examples and trace contents.

For agent-based LangSmith workspaces, use a current SDK supporting `agent_address`; create an Observability agent in the UI and configure its ID and environment. Project-based workspaces use the tracing project named in the notebook. Use the API endpoint matching your LangSmith region, and a workspace ID if needed. The SDK range allows upgrades; exact versions are not locked.

The essentials are nested tracing, error inspection, labeled datasets, a code evaluator, and two prompt experiments. No agents, vector database, or paid judge model is required. API keys must not be committed.
