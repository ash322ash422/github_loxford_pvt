"""
Entry point for the Marketing Campaign Analysis Agent project.

Run with:
    python main.py

To try the optional LLM-powered copilot:
    1. pip install -r requirements.txt
    2. cp .env.example .env      (then edit .env and paste in your real key)
    3. change use_llm to True below
"""

# Load variables from a local .env file (like API_KEY) into the
# environment, so the CopilotAgent's client can find
# the key without you having to export it manually every terminal session.
# Wrapped in try/except so the project still runs fine even if a student
# hasn't installed python-dotenv -- they just won't get .env support.

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from orchestrator import Orchestrator

if __name__ == "__main__":
    orchestrator = Orchestrator(csv_path="data/campaign_data.csv", use_llm=False)
    # orchestrator = Orchestrator(csv_path="data/campaign_data.csv", use_llm=False)
    
    report = orchestrator.run()
    print(report)
