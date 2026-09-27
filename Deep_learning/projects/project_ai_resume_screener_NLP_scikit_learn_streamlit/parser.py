"""
parser.py — Resume & Job Description Parser
Extracts structured fields from raw text using spaCy NER + regex patterns.
"""

import re
import nltk
import spacy
from typing import Optional

# Download required NLTK data
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords", quiet=True)


def load_spacy_model():
    """Load spaCy model, fallback to blank English if not installed."""
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        return spacy.blank("en")


nlp = load_spacy_model()

# --- Regex patterns ---
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]")
LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w\-]+", re.IGNORECASE)
GITHUB_RE = re.compile(r"github\.com/[\w\-]+", re.IGNORECASE)

EDUCATION_KEYWORDS = [
    "bachelor", "master", "phd", "doctorate", "b.sc", "m.sc", "b.tech",
    "m.tech", "mba", "b.e", "m.e", "b.com", "degree", "university",
    "college", "institute", "graduation", "diploma", "associate"
]

EXPERIENCE_KEYWORDS = [
    "experience", "work", "employment", "career", "internship",
    "position", "role", "responsibilities", "worked at", "working at"
]

SECTION_HEADERS = re.compile(
    r"^\s*(education|experience|skills|projects|certifications|"
    r"awards|summary|objective|profile|work history|employment|"
    r"technical skills|core competencies)\s*[:\-]?\s*$",
    re.IGNORECASE | re.MULTILINE
)


def extract_name(text: str) -> str:
    """Extract candidate name using spaCy NER (first PERSON entity)."""
    doc = nlp(text[:500])
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()
    # Fallback: first non-empty line
    for line in text.split("\n"):
        line = line.strip()
        if line and len(line.split()) <= 4 and not EMAIL_RE.search(line):
            return line
    return "Unknown"


def extract_email(text: str) -> str:
    match = EMAIL_RE.search(text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    match = PHONE_RE.search(text)
    return match.group(0).strip() if match else ""


def extract_links(text: str) -> dict:
    return {
        "linkedin": (LINKEDIN_RE.search(text) or [""])[0] if LINKEDIN_RE.search(text) else "",
        "github":   (GITHUB_RE.search(text) or [""])[0] if GITHUB_RE.search(text) else "",
    }


def extract_years_experience(text: str) -> Optional[float]:
    """Heuristic: find patterns like '3 years', '5+ years of experience'."""
    patterns = [
        r"(\d+)\+?\s*years?\s+of\s+experience",
        r"(\d+)\+?\s*years?\s+experience",
        r"experience\s+of\s+(\d+)\+?\s*years?",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def extract_education(text: str) -> list:
    """Return lines that contain education-related keywords."""
    results = []
    for line in text.split("\n"):
        if any(kw in line.lower() for kw in EDUCATION_KEYWORDS):
            clean = line.strip()
            if clean and len(clean) > 5:
                results.append(clean)
    return list(dict.fromkeys(results))  # deduplicate preserving order


def parse_resume(text: str) -> dict:
    """
    Full resume parser. Returns structured dict with all extracted fields.
    """
    text = text.strip()
    links = extract_links(text)
    return {
        "name":        extract_name(text),
        "email":       extract_email(text),
        "phone":       extract_phone(text),
        "linkedin":    links["linkedin"],
        "github":      links["github"],
        "years_exp":   extract_years_experience(text),
        "education":   extract_education(text),
        "raw_text":    text,
    }


def parse_job_description(text: str) -> dict:
    """
    Parse job description into structured form.
    Returns title heuristic, required experience, raw text.
    """
    text = text.strip()
    title = ""
    for line in text.split("\n")[:5]:
        line = line.strip()
        if line and len(line) < 80:
            title = line
            break
    return {
        "title":    title,
        "years_required": extract_years_experience(text),
        "raw_text": text,
    }
