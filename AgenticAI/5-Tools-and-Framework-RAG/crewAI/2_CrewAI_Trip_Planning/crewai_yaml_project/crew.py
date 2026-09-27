from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task

from tools import web_search


@CrewBase
class TripCrew:
    """Trip-planning crew, configured from YAML."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self):
        # Same cost guardrails as Project 1: capped response length, capped
        # think/act iterations, and a wall-clock backstop per agent.
        self.llm = LLM(model="gpt-4o-mini", temperature=0.4, max_tokens=600)

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            tools=[web_search],
            llm=self.llm,
            max_iter=6,
            max_execution_time=90,
            verbose=True,
        )

    @agent
    def writer(self) -> Agent:
        return Agent(
            config=self.agents_config["writer"],
            llm=self.llm,
            max_iter=6,
            max_execution_time=90,
            verbose=True,
        )

    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config["research_task"], agent=self.researcher())

    @task
    def writing_task(self) -> Task:
        return Task(config=self.tasks_config["writing_task"], agent=self.writer())

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,   # populated automatically from @agent methods
            tasks=self.tasks,     # populated automatically from @task methods, in definition order
            process=Process.sequential,
            verbose=True,
        )
