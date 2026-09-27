# agent.py
# This script can run stand alone

from dotenv import load_dotenv
load_dotenv()

import os
import sys
import tempfile
import subprocess
from typing import Optional
from pydantic import Field
from langchain_core.tools import BaseTool
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent


# Define the Code Generation Tool
class CodeGenerationTool(BaseTool):
    llm: ChatOpenAI = Field()

    name: str = "code_generator"
    description: str = "Generates code for specified programming tasks"

    def _run(self, task: str) -> str:
        code_prompt = PromptTemplate(
            template="""Generate clean, efficient code for the task:
            {task}
            
            Guidelines:
            - Use best practices
            - Include minimal comments
            - Ensure the code is executable""",
            input_variables=["task"]
        )

        prompt = code_prompt.format(task=task)
        response = self.llm.invoke(prompt)

        return response.content


# Define the Code Execution Tool
class CodeExecutionTool(BaseTool):
    name: str = "code_executor"
    description: str = "Executes generated code in a sandbox"

    def _run(self, code: str, language: str = 'python') -> str:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{language}', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name

            result = subprocess.run(
                [sys.executable, temp_file_path],
                capture_output=True,
                text=True,
                timeout=10,
                check=True
            )

            return result.stdout

        except subprocess.TimeoutExpired:
            return "Code execution timed out."
        except subprocess.CalledProcessError as e:
            return f"Error executing code: {e.stderr}"
        finally:
            if 'temp_file_path' in locals():
                os.unlink(temp_file_path)


# Create the Code Agent
def create_code_agent(api_key: Optional[str] = None):
    llm = ChatOpenAI(
        api_key=api_key or os.getenv('OPENAI_API_KEY'),
        model="gpt-4o-mini",
        temperature=0.0,
        # max_tokens=1000,
    )

    if not llm:
        raise ValueError("OpenAI API key required")

    # Initialize tools
    code_generator_tool = CodeGenerationTool(llm=llm)
    code_executor_tool = CodeExecutionTool()

    tools = [code_generator_tool, code_executor_tool]

    # Initialize the agent (new LangChain 1.x prebuilt agent, LangGraph-based)
    agent = create_agent(
        model=llm,
        tools=tools,
    )

    return agent


def print_trace(messages):
    """Print each step of the agent run, highlighting tool calls and results."""
    for msg in messages:
        msg_type = type(msg).__name__

        if msg_type == "HumanMessage":
            print(f"[user] {msg.content}")

        elif msg_type == "AIMessage" and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                print(f"[tool call] {tc['name']}({tc['args']})")
            if msg.content:
                print(f"[agent] {msg.content}")

        elif msg_type == "ToolMessage":
            print(f"[tool result: {msg.name}] {msg.content}")

        elif msg_type == "AIMessage":
            print(f"[agent] {msg.content}")




# Main function
def main():
    agent = create_code_agent()

    TASKS = [
        "Generate a Python function for addition, then execute it with the \
            inputs 5 and 7. Show me the code and tell me the result.",
            
        "Generate a Python script that calculates the first 10 Fibonacci numbers, \
            then execute it and show me the code and result.",
            
        "Create a script in python to calculate value of PI upto 4 decimals using random numbers.\
            Execute this and show me the result",
    ]

    for task in TASKS:
        print(f"\n--- Task: {task} ---")
        response = agent.invoke({"messages": [{"role": "user", "content": task}]})
        print_trace(response["messages"]) # OPTIONAL
        print(f"\n[final answer] {response['messages'][-1].content}")


if __name__ == "__main__":
    main()