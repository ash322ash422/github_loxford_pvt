# Prompt Used to Create the Automated Data Analysis Project

You are a senior Python and AI-agent developer.

Build a student-friendly AI-powered automated data analysis application called **Automated Data Analysis Crew**.

The application should analyze a CSV or Excel file containing student performance data, including:

- Student information
- Gender and grade level
- Student group
- Attendance rate
- Study hours
- Assignment completion
- Midterm score
- Final score
- Participation rate

Use Python, CrewAI, OpenAI, Pandas, NumPy, Matplotlib, Seaborn, SciPy, `python-dotenv`, and pytest.

## AI Agent Workflow

Use a real CrewAI sequential workflow with `Process.sequential`.

Create these agents:

1. **Data Profiler Agent**
   - Inspect columns and data types
   - Count rows and columns
   - Find missing values
   - Find duplicate records
   - Detect numerical and categorical columns
   - Detect possible outliers

2. **Data Cleaning Agent**
   - Remove duplicate rows
   - Fill missing numerical values using the median
   - Fill missing categorical values with `"Unknown"`
   - Save the cleaned dataset
   - Produce a cleaning summary

3. **Data Analyst Agent**
   - Calculate descriptive statistics
   - Calculate group averages
   - Analyze distributions
   - Calculate correlations
   - Use Python tools for all numerical calculations

4. **Visualization Agent**
   - Create distribution charts
   - Create a correlation heatmap
   - Save all charts as image files
   - Return the chart paths

5. **Insight Agent**
   - Interpret the calculated results
   - Identify important patterns
   - Explain relationships
   - Separate observations from assumptions
   - Provide actionable recommendations
   - Never invent numerical values

6. **Report Writer Agent**
   - Write a Markdown report for faculty
   - Include an executive summary
   - Explain the data-cleaning process
   - Present analysis findings
   - Include insights, recommendations, limitations, and visualization links

7. **Quality Review Agent**
   - Check the calculations and report
   - Verify that claims are supported by the analysis
   - Check that charts and files exist
   - Check report completeness
   - Return either `APPROVED` or `REVISE` with explanations

## OpenAI Configuration

Use an explicit OpenAI LLM through CrewAI:

```python
from crewai import LLM

llm = LLM(
    model=os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini"),
    temperature=0.2,
    api_key=os.getenv("OPENAI_API_KEY"),
)
```

Every CrewAI agent must receive this same `llm` instance.

Load credentials from a `.env` file using `python-dotenv`:

```dotenv
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=openai/gpt-4o-mini
```

If the API key is missing, raise a clear error. Never print or expose the API key. Add `.env` to `.gitignore`.

## Tool and AI Responsibilities

Python tools must perform:

- Dataset loading
- Data profiling
- Data cleaning
- Statistical calculations
- Correlation calculations
- Chart generation
- File validation

The OpenAI agents must perform:

- Reasoning
- Interpretation
- Insight generation
- Recommendation generation
- Report writing
- Quality review

Do not allow the LLM to manually calculate statistics or invent values.

The AI-generated output from the Insight Agent, Report Writer Agent, and Quality Review Agent must be used in the final report. Do not replace the AI report with a separate deterministic report.

## Command-Line Usage

The application should run with:

```powershell
python main.py data\input\student_performance.csv --output output
```

There must be only one execution mode. The application must always use CrewAI and OpenAI.

The final command-line output should show the paths of:

- The cleaned dataset
- Generated visualizations
- The final Markdown report

## Required Output

Generate:

- `cleaned_data.csv`
- `analysis_report.md`
- Dataset profile information
- Cleaning summary
- Analysis results
- Distribution charts
- Correlation heatmap
- AI-generated insights
- AI-generated recommendations
- AI quality review

Use Matplotlib’s non-GUI backend so charts work correctly from the command line:

```python
import matplotlib
matplotlib.use("Agg")
```

## Testing and Documentation

Add tests for:

- Dataset loading
- Missing values
- Duplicate records
- Data cleaning
- Statistical analysis
- Visualization creation
- Report generation
- Quality validation

Run:

```powershell
python -m pytest tests -q
python -m compileall -q src main.py tests
```

Create a README explaining:

- What the project does
- What each AI agent does
- What each Python tool does
- How to configure `.env`
- How to run the project
- What files are generated
- How to run the tests

Implement the complete working project, not just a plan or code examples.