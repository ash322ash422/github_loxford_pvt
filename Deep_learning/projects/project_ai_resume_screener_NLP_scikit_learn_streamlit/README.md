# 🤖 AI Resume Screening System

An intelligent, NLP + Deep Learning powered resume screening system built with Python and Streamlit. It automatically parses resumes, matches skills against job descriptions, and ranks candidates using BERT semantic embeddings — giving recruiters a fast, data-driven shortlist.

---

## 📐 Architecture Overview

```
Job Description ──┐
                  ▼
Resume Text ──► Parser ──► Skill Extractor ──► Skill Match Score (40%) ──┐
                  │                                                         ▼
                  └──► BERT Encoder ──► Semantic Score (60%) ──► Composite Ranker ──► Ranked Output
```

### System Components

| Module | File | Role |
|---|---|---|
| **Resume Parser** | `parser.py` | Extracts name, email, phone, education, experience using spaCy NER + regex |
| **Skill Matcher** | `skill_matcher.py` | TF-IDF + keyword matching against 80+ tech skill vocabulary |
| **Semantic Ranker** | `semantic_ranker.py` | BERT embeddings via `sentence-transformers` for deep semantic similarity |
| **Recommender** | `recommender.py` | Composite scoring, ranking, and recommendation labelling |
| **UI** | `app.py` | Streamlit dashboard with visualisations |

---

## 🔁 Workflow Logic

### Step 1 — Parsing
Both the job description and each resume are fed through `parser.py`:
- **spaCy NER** identifies the candidate's name (PERSON entity)
- **Regex patterns** extract email, phone, LinkedIn, GitHub, and years of experience
- **Keyword search** over section headers finds education entries

### Step 2 — Skill Matching (TF-IDF + Vocabulary)
`skill_matcher.py` compares extracted skills:
1. Both texts are normalised (lowercase, strip punctuation)
2. A curated 80+ term vocabulary of tech skills is scanned via regex in both the resume and JD
3. **Skill Match Score** = `(matched skills ∩ required skills) / required skills × 100`
4. Falls back to TF-IDF cosine similarity if no vocabulary skills are detected

### Step 3 — Semantic Ranking (BERT Deep Learning)
`semantic_ranker.py` uses the `all-MiniLM-L6-v2` sentence-transformer:
1. All resume texts + the JD are **batch-encoded** into 384-dimensional vectors
2. **Cosine similarity** is computed between each resume embedding and the JD embedding
3. **Semantic Score** = `cosine_similarity × 100` — captures contextual relevance beyond keywords

### Step 4 — Composite Scoring & Ranking
`recommender.py` combines all signals:

```
Base Score  = (0.40 × Skill Match Score) + (0.60 × Semantic Score)
Exp Bonus   = min(experience_gap × 2.0, 10)       # bonus for matching/exceeding JD requirements
Final Score = min(Base Score + Exp Bonus, 100)
```

| Final Score | Label |
|---|---|
| ≥ 80 | 🟢 Highly Recommended |
| 60 – 79 | 🟡 Recommended |
| 40 – 59 | 🟠 Consider |
| < 40 | 🔴 Not Recommended |

---

## 📁 Project Structure

```
ai_resume_screener/
├── app.py                    # Streamlit UI — entry point
├── parser.py                 # Resume & JD parsing (spaCy + regex)
├── skill_matcher.py          # TF-IDF skill matching
├── semantic_ranker.py        # BERT embedding semantic ranker
├── recommender.py            # Composite scoring & ranking
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── sample_resumes/
    ├── priya_sharma.txt      # Senior ML Engineer (strong match)
    ├── aisha_khan.txt        # Data Scientist (strong match)
    ├── rahul_verma.txt       # Software Engineer (partial match)
    ├── sneha_patel.txt       # DevOps Engineer (partial match)
    └── arjun_mehta.txt       # Fresh Graduate (weak match)
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python **3.10+**
- pip

### 1. Clone or download the project
```bash
git clone https://github.com/your-username/ai-resume-screener.git
cd ai_resume_screener
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv

# Activate on macOS/Linux:
source venv/bin/activate

# Activate on Windows:
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Download spaCy language model
```bash
python -m spacy download en_core_web_sm
```

> **Note:** The `sentence-transformers` model (`all-MiniLM-L6-v2`, ~80MB) is downloaded automatically on first run. Ensure you have an internet connection.

---

## 🚀 Running the App

```bash
streamlit run app.py
```

The app opens in your browser at **`http://localhost:8501`**

---

## 🖥️ Using the App

### Tab 1 — Input & Screen
1. **Job Description** — paste or toggle the built-in sample JD
2. **Resumes** — choose one of three input modes:
   - `Load sample resumes` — instantly loads 5 pre-built resumes
   - `Paste resume text` — manually paste 1–10 resumes
   - `Upload .txt files` — upload plain-text resume files
3. Click **🚀 Screen Candidates** — the pipeline runs in real time

### Tab 2 — Analysis
- Grouped bar chart comparing skill, semantic, and final scores
- Score distribution histogram
- Recommendation breakdown pie chart
- Full sortable results table with CSV download

### Tab 3 — Candidate Details
- Per-candidate score gauges (skill / semantic / final)
- Matched and missing skill chips
- Skill coverage radar chart against JD requirements
- Education timeline
- Raw resume text viewer

---

## 🛠️ Customisation

### Adjust scoring weights
In the sidebar (or directly in `recommender.py`):
```python
SKILL_WEIGHT    = 0.40   # keyword skill match
SEMANTIC_WEIGHT = 0.60   # BERT semantic similarity
```

### Extend the skill vocabulary
In `skill_matcher.py`, add terms to `SKILL_VOCAB`:
```python
SKILL_VOCAB = {
    ...,
    "langchain", "llama", "stable diffusion",   # add new skills
}
```

### Swap the embedding model
In `semantic_ranker.py`:
```python
_MODEL_NAME = "all-mpnet-base-v2"   # larger, more accurate (420MB)
# or
_MODEL_NAME = "paraphrase-MiniLM-L3-v2"  # smaller, faster
```

---

## 📦 Key Dependencies

| Package | Version | Purpose |
|---|---|---|
| `streamlit` | ≥1.28 | Web UI framework |
| `spacy` | ≥3.6 | NLP / NER for parsing |
| `sentence-transformers` | ≥2.2 | BERT semantic embeddings |
| `scikit-learn` | ≥1.3 | TF-IDF, cosine similarity |
| `torch` | ≥2.0 | Deep learning backend |
| `plotly` | ≥5.15 | Interactive charts |
| `pandas` | ≥2.0 | Data handling / CSV export |
| `nltk` | ≥3.8 | Text preprocessing |

---

## 🧪 Sample Output

Given the built-in ML Engineer JD, the 5 sample resumes rank approximately as:

| Rank | Candidate | Final Score | Status |
|---|---|---|---|
| 1 | Aisha Khan | ~85% | 🟢 Highly Recommended |
| 2 | Priya Sharma | ~82% | 🟢 Highly Recommended |
| 3 | Rahul Verma | ~55% | 🟠 Consider |
| 4 | Sneha Patel | ~48% | 🟠 Consider |
| 5 | Arjun Mehta | ~22% | 🔴 Not Recommended |

---

## 📄 License

MIT License — free to use, modify, and distribute.
