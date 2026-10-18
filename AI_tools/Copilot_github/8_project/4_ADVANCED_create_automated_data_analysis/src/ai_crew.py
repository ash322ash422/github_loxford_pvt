from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool
from dotenv import load_dotenv

from .tools.analysis_tools import analyze_dataset
from .tools.data_tools import clean_dataset, load_dataset, profile_dataset
from .tools.visualization_tools import create_visualizations


def run_agent_crew(dataset_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Run the seven-agent sequential analysis workflow."""
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env", override=False)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        raise RuntimeError(
            f"Set OPENAI_API_KEY in {project_root / '.env'} before running the AI crew."
        )
    llm = LLM(
        model=os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini"),
        temperature=0.2,
        api_key=api_key,
    )
    source = Path(dataset_path).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    state = output / ".crew_state"
    state.mkdir(exist_ok=True)

    @tool("profile_dataset")
    def profile_tool() -> str:
        """Profile the input dataset and save profile.json."""
        profile = profile_dataset(load_dataset(source))
        (state / "profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
        return json.dumps(profile)

    @tool("clean_dataset")
    def clean_tool() -> str:
        """Clean duplicates and missing values and save cleaned_data.csv and cleaning.json."""
        cleaned, summary = clean_dataset(load_dataset(source))
        cleaned.to_csv(output / "cleaned_data.csv", index=False)
        (state / "cleaning.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return json.dumps(summary)

    @tool("analyze_cleaned_dataset")
    def analysis_tool() -> str:
        """Analyze output/cleaned_data.csv and save analysis.json."""
        analysis = analyze_dataset(load_dataset(output / "cleaned_data.csv"))
        analysis["row_count"] = int(len(load_dataset(output / "cleaned_data.csv")))
        (state / "analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        return json.dumps(analysis)

    @tool("create_visualizations")
    def visualization_tool() -> str:
        """Create charts from output/cleaned_data.csv in output/visualizations."""
        paths = create_visualizations(
            load_dataset(output / "cleaned_data.csv"), output / "visualizations"
        )
        (state / "visualizations.json").write_text(json.dumps(paths, indent=2), encoding="utf-8")
        return json.dumps(paths)

    agents = [
        Agent(
            role="Data Profiler",
            goal="Inspect the dataset and produce a complete, accurate data-quality profile.",
            backstory="You are a meticulous data quality specialist. Always use the profiling tool before making claims.",
            tools=[profile_tool],
            llm=llm,
            allow_delegation=False,
        ),
        Agent(
            role="Data Cleaning Specialist",
            goal="Create a trustworthy cleaned dataset using the profile and document every cleaning decision.",
            backstory="You apply conservative, reproducible cleaning rules and never invent source data.",
            tools=[clean_tool],
            llm=llm,
            allow_delegation=False,
        ),
        Agent(
            role="Data Analyst",
            goal="Calculate descriptive statistics, group comparisons, distributions, and correlations from the cleaned data.",
            backstory="You are a quantitative analyst. All numerical claims must come from the analysis tool.",
            tools=[analysis_tool],
            llm=llm,
            allow_delegation=False,
        ),
        Agent(
            role="Visualization Specialist",
            goal="Select and generate useful visualizations for the calculated analysis.",
            backstory="You create clear charts that directly support findings and save every chart to the requested output folder.",
            tools=[visualization_tool],
            llm=llm,
            allow_delegation=False,
        ),
        Agent(
            role="Insight Analyst",
            goal="Interpret the profile, cleaning summary, analysis, and charts into evidence-based insights.",
            backstory="You distinguish observations from assumptions, mention limitations, and never fabricate numbers.",
            llm=llm,
            allow_delegation=False,
        ),
        Agent(
            role="Report Writer",
            goal="Prepare a concise faculty-ready report using the complete analysis package.",
            backstory="You communicate technical results clearly with an executive summary, methods, findings, charts, and recommendations.",
            llm=llm,
            allow_delegation=False,
        ),
        Agent(
            role="Quality Reviewer",
            goal="Audit the analysis package and report for consistency, unsupported claims, and missing outputs.",
            backstory="You are an independent reviewer. Approve only evidence-backed and complete work; list corrections otherwise.",
            llm=llm,
            allow_delegation=False,
        ),
    ]
    dataset_text = str(source)
    tasks: list[Task] = []
    tasks.append(Task(
            description=f"Use profile_dataset on {dataset_text}. Save the result to the required state file and summarize its findings.",
            expected_output="A factual dataset profile with dimensions, types, missing values, duplicates, and outliers.",
            agent=agents[0],
        ))
    tasks.append(Task(
            description=f"Use clean_dataset on {dataset_text}. Use the profile from the previous task, save the cleaned CSV and cleaning summary, and explain the decisions.",
            expected_output="A cleaning summary confirming the cleaned dataset path and changes made.",
            agent=agents[1],
            context=[tasks[0]],
        ))
    tasks.append(Task(
            description="Use analyze_cleaned_dataset on the cleaned CSV produced by the previous task. Report only calculated results.",
            expected_output="Descriptive statistics, group means, distributions, correlations, and row count.",
            agent=agents[2],
            context=[tasks[1]],
        ))
    tasks.append(Task(
            description="Use create_visualizations on the cleaned CSV. Explain which generated charts support the analysis.",
            expected_output="A list of chart paths and a short explanation of their purpose.",
            agent=agents[3],
            context=[tasks[2]],
        ))
    tasks.append(Task(
            description="Interpret the previous task outputs. Produce structured insights, unusual findings, limitations, and actionable recommendations. Do not invent values.",
            expected_output="Evidence-based insights and recommendations grounded in the tool outputs.",
            agent=agents[4],
            context=[tasks[0], tasks[1], tasks[2], tasks[3]],
        ))
    tasks.append(Task(
            description=f"Draft the final Markdown report for the faculty using all previous outputs. The report will be written to {output / 'analysis_report.md'} by the application.",
            expected_output="A complete report draft with summary, methods, findings, visualizations, insights, recommendations, and limitations.",
            agent=agents[5],
            context=[tasks[0], tasks[1], tasks[2], tasks[3], tasks[4]],
        ))
    tasks.append(Task(
            description="Review every prior output and the report draft. State APPROVED or REVISE, then list concrete consistency or completeness issues.",
            expected_output="A quality decision with checks and any required revisions.",
            agent=agents[6],
            context=[tasks[0], tasks[1], tasks[2], tasks[3], tasks[4], tasks[5]],
        ))
    crew = Crew(agents=agents, tasks=tasks, process=Process.sequential, verbose=True)
    result = crew.kickoff()
    task_outputs = [str(task_output) for task_output in result.tasks_output]
    report = task_outputs[5].strip()
    review = task_outputs[6].strip()
    report_path = output / "analysis_report.md"
    report_path.write_text(
        report
        + "\n\n## AI Insights\n\n"
        + task_outputs[4].strip()
        + "\n\n## Quality Review\n\n"
        + review
        + "\n",
        encoding="utf-8",
    )
    return {
        "task_outputs": task_outputs,
        "insights": task_outputs[4],
        "report": report,
        "quality_review": review,
        "report_path": str(report_path),
        "state_dir": str(state),
        "crew_result": str(result),
    }
