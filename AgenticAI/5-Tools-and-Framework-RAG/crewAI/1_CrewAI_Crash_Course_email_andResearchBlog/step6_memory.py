# Now we add memory: This code took 3-5 minutes to run

from dotenv import load_dotenv
load_dotenv()

from crewai import LLM

llm = LLM(
    # model="gemini/gemini-2.0-flash",
    model="openai/gpt-5-nano",

)

from crewai import Agent, Task, Crew
from crewai_tools import SerperDevTool

research_agent = Agent(
    role="Research Specialist",
    goal="Research interesting facts about the topic: {topic}",
    backstory="You are an expert at finding relevant and factual data.",
    tools=[SerperDevTool()],
    verbose=True,
    llm=llm
)

writer_agent = Agent(
    role="Creative Writer",
    goal="Write a short blog summary using the research",
    backstory="You are skilled at writing engaging summaries based on provided content.",
    llm=llm,
    verbose=True,
)

task_research = Task(
    description="Find 3-5 interesting and recent facts about {topic} as of year 2025.",
    expected_output="A bullet list of 3-5 facts",
    agent=research_agent,
)

task_blog = Task(
    description="Write a 100-word blog post summary about {topic} using the facts from the research.",
    expected_output="A blog post summary",
    agent=writer_agent,
    context=[task_research],
)

crew = Crew(
    agents = [research_agent, writer_agent],
    tasks  = [task_research, task_blog],
    verbose = True,
    memory  =True, # previous conversation would be stored
    embedder = {   # Use embedding for searching the memory
        "provider": "openai",
        "config": { "model": "text-embedding-3-small" }
    }
    
)

crew.kickoff(inputs={"topic": "The future of solar panels"})

# Follow up question: I am not mentioning the topic. It should remember.
crew.kickoff(inputs={"topic": "What is the revenue outlook in this sector?"}) 