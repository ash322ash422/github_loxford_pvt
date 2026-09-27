"""simple_agent.py

Minimal OpenAI-based agent example.

Purpose:
- Demonstrates a tiny "agent" wrapper around an OpenAI LLM.
- Shows capabilities and a short use-case description usable in documentation.

Usage:
1. Install the OpenAI Python client: `pip install openai`
2. Set your API key in the environment:
   - Windows (PowerShell): $env:OPENAI_API_KEY = "sk-..."
   - macOS / Linux: export OPENAI_API_KEY="sk-..."
3. Run: `python simple_agent.py`

Notes:
- This example is intentionally minimal and synchronous.
- Do NOT hardcode your API key in source code.
"""

from typing import Optional
import os
import openai

# Describe the agent's capabilities and use case (for documentation)
CAPABILITIES = [
    "Answer questions using an LLM",
    "Summarize text",
    "Generate plain-text responses based on prompts",
]

USE_CASE = (
    "A small instructional agent for demonstrating how to wrap an OpenAI LLM. "
    "Good for prototypes, docs, and simple task automation where you send a prompt "
    "and receive a text response."
)


class SimpleAgent:
    """A tiny wrapper around OpenAI's chat API providing a simple `ask` method.

    Methods
    -------
    ask(prompt, system=None):
        Send a prompt to the model and return the assistant's text response.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set in environment and no api_key provided")
        openai.api_key = key
        self.model = model

    def ask(self, prompt: str, system: Optional[str] = None, temperature: float = 0.2) -> str:
        """Send a prompt and return the model's textual reply.

        Parameters
        ----------
        prompt : str
            The user's prompt or instruction for the model.
        system : str, optional
            Optional system message to steer the assistant's behavior.
        temperature : float
            Sampling temperature for randomness (0.0 - 1.0).
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=600,
        )
        # Safely extract content
        choices = resp.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "").strip()


def main():
    print("Agent capabilities:")
    for c in CAPABILITIES:
        print("-", c)
    print("\nUse case:", USE_CASE)

    # Demo: create agent and ask a simple question
    try:
        agent = SimpleAgent()
    except RuntimeError as err:
        print("Missing API key:", err)
        print("Set OPENAI_API_KEY and re-run the script.")
        return

    prompt = "Explain briefly what an agent is and give one practical use case."
    print("\nPrompt:\n", prompt)
    answer = agent.ask(prompt)
    print("\nAgent response:\n", answer)


if __name__ == "__main__":
    main()
