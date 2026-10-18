# Automated Data Analysis Crew

This project implements the requested sequential analysis flow with a real
CrewAI `Process.sequential` crew:

1. Profile the raw dataset.
2. Clean duplicates and missing values.
3. Calculate deterministic descriptive statistics, group means, and correlations.
4. Create distribution plots and a correlation heatmap.
5. Generate evidence-based insights.
6. An Insight Agent interprets the calculated evidence.
7. A Report Agent prepares the faculty-facing report.
8. A Quality Review Agent audits the complete package.

Numerical calculations are performed by Pandas/NumPy tools rather than by an
LLM. The agents decide, orchestrate, interpret, write, and review; tools perform
the calculations. The normal CLI path therefore requires a CrewAI-supported LLM
configuration such as `OPENAI_API_KEY`.

The crew explicitly uses CrewAI's OpenAI adapter with
`openai/gpt-4o-mini` by default. Set `OPENAI_MODEL` to select another OpenAI
model. The Insight Agent, Report Agent, and Quality Review Agent outputs are
used as the actual report content; Python is used for calculations, charts,
validation, and file handling.

## Run

```powershell
cd automated_data_analysis

python -m pip install -r requirements.txt

python main.py data\input\student_performance.csv --output output

```

Configure OpenAI before running:

Edit the `.env` file in the project directory:

```dotenv
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=openai/gpt-4o-mini
```

The application loads this file automatically with `python-dotenv`. An
environment variable already set in the shell takes precedence over `.env`.

Alternatively, configure the variables for the current PowerShell session:

```powershell
$env:OPENAI_API_KEY="your-api-key"
$env:OPENAI_MODEL="openai/gpt-4o-mini"
```

The output directory contains `cleaned_data.csv`, a `visualizations` folder,
and `analysis_report.md`. The pipeline accepts CSV and Excel files. CrewAI is
always used; there is no non-agent execution mode.

Charts use Matplotlib's non-GUI `Agg` backend, so command-line and CrewAI
threaded execution does not start Tkinter windows or emit GUI cleanup warnings.

## Test

```powershell
python -m pytest tests
```

The application quality gate checks that cleaning removed all missing values,
the analysis row count matches the cleaned dataset, every chart exists, and at
least one insight is available. A failed check raises an error instead of
writing a success-shaped report.
