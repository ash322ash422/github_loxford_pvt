
**How it works**
1. Set `PROVIDER` to `"openai"`, `"gemini"` or `"cohere"`, and paste your API key when prompted.
2. It reads `job_description.txt` and the PDF, DOCX and TXT files in `resumes/`. If those are missing, it uses built-in sample data so it runs immediately.
3. Emails and phone numbers are redacted before anything is sent to the LLM.
4. For each resume, the LLM returns JSON scores from 0 to 100 for skills match, experience relevance, achievements and education. It also returns missing must-haves, strengths, gaps, a summary and a recommendation (`strong_yes`, `yes`, `maybe` or `no`).
5. Output is checked against a pydantic schema, and bad output is retried up to three times.
6. The final score is computed in code, not by the LLM: a weighted sum using `WEIGHTS`, minus 10 points per missing must-have.
7. Candidates are ranked and shown in a table with per-candidate detail, and exported to `ranked_candidates.csv`.

**Models used (change in `MODELS`)**
- OpenAI: `gpt-4o-mini`
- Gemini: `gemini-2.5-flash`
- Cohere: `command-a-03-2025`

Resumes are scored in parallel with 4 workers. A resume that fails is reported separately and doesn't stop the run.

Candidate names are still sent to the LLM, and only emails and phone numbers are redacted. If you need names stripped too, that's a small change to the redaction step.