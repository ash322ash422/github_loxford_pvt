"""
skill_matcher.py — TF-IDF + keyword-based skill matching
Compares candidate skills against job description requirements.
"""

import re
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
from typing import Tuple

try:
    STOPWORDS = set(stopwords.words("english"))
except LookupError:
    nltk.download("stopwords", quiet=True)
    STOPWORDS = set(stopwords.words("english"))

# ── Comprehensive tech skills vocabulary ──────────────────────────────────────
SKILL_VOCAB = {
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl", "bash",
    
    # Web
    "html", "css", "react", "angular", "vue", "node.js", "django", "flask",
    "fastapi", "spring", "express", "next.js", "nuxt", "svelte", "tailwind",
    
    # Data / ML / AI
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
    "matplotlib", "seaborn", "plotly", "huggingface", "transformers",
    "bert", "gpt", "llm", "reinforcement learning", "xgboost", "lightgbm",
    
    # Databases
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "cassandra", "dynamodb", "sqlite", "oracle", "neo4j",
    
    # Cloud / DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "github actions", "ci/cd", "linux", "git",
    
    # Data Engineering
    "spark", "hadoop", "kafka", "airflow", "dbt", "etl", "data pipeline",
    "snowflake", "bigquery", "redshift",
    
    # Soft / general
    "agile", "scrum", "rest api", "graphql", "microservices", "oop",
    "data structures", "algorithms", "system design",
}


def normalize(text: str) -> str:
    """Lowercase and strip punctuation (keep hyphens for c++, node.js etc.)."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\.\+\# ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_skills_from_text(text: str) -> list[str]:
    """
    Return matched skills from SKILL_VOCAB found in the text.
    Handles multi-word skills (e.g. 'machine learning', 'deep learning').
    """
    norm = normalize(text)
    found = []
    # Sort by length desc so longer phrases match before substrings
    for skill in sorted(SKILL_VOCAB, key=len, reverse=True):
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, norm):
            found.append(skill)
    return found


def skill_match_score(resume_text: str, jd_text: str) -> Tuple[float, list, list, list]:
    """
    Compute a skill-match score between a resume and job description.

    Returns:
        score        (float 0–100)
        matched      (list of matched skills)
        missing      (list of skills in JD but not in resume)
        candidate_skills (all skills found in resume)
    """
    jd_skills       = set(extract_skills_from_text(jd_text))
    candidate_skills = set(extract_skills_from_text(resume_text))

    if not jd_skills:
        # No skills detected in JD — fall back to TF-IDF overlap
        score = _tfidf_overlap(resume_text, jd_text) * 100
        return round(score, 2), [], [], list(candidate_skills)

    matched = jd_skills & candidate_skills
    missing = jd_skills - candidate_skills

    # Weighted: each matched skill contributes equally
    score = (len(matched) / len(jd_skills)) * 100

    return round(score, 2), sorted(matched), sorted(missing), sorted(candidate_skills)


def _tfidf_overlap(text_a: str, text_b: str) -> float:
    """Cosine similarity via TF-IDF as a fallback score."""
    try:
        vec = TfidfVectorizer(stop_words="english", max_features=500)
        tfidf = vec.fit_transform([normalize(text_a), normalize(text_b)])
        return float(cosine_similarity(tfidf[0], tfidf[1])[0][0])
    except Exception:
        return 0.0


def batch_skill_scores(resumes: list[dict], jd_text: str) -> list[dict]:
    """
    Add skill match fields to each resume dict in place.
    Each dict must have a 'raw_text' key.
    """
    for r in resumes:
        score, matched, missing, all_skills = skill_match_score(r["raw_text"], jd_text)
        r["skill_score"]      = score
        r["matched_skills"]   = matched
        r["missing_skills"]   = missing
        r["candidate_skills"] = all_skills
    return resumes
