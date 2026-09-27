"""
semantic_ranker.py — BERT-based semantic similarity ranking
Uses sentence-transformers to encode resumes and JD into embeddings,
then ranks candidates by cosine similarity.
"""
# TODO: For students -- Implement the _get_model()

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Lazy-load the model to avoid slow startup
_model = None
_MODEL_NAME = "all-MiniLM-L6-v2"  # Fast, lightweight, good quality


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(_MODEL_NAME)
        except Exception as e:
            print(f"[semantic_ranker] Warning: Could not load sentence-transformer: {e}")
            _model = None
    return _model


def encode_text(text: str) -> np.ndarray | None:
    """Encode a single text into a sentence embedding."""
    model = _get_model()
    if model is None:
        return None
    return model.encode([text], convert_to_numpy=True)[0]


def encode_texts(texts: list[str]) -> np.ndarray | None:
    """Batch encode a list of texts into sentence embeddings."""
    model = _get_model()
    if model is None:
        return None
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=False)


def semantic_similarity(resume_text: str, jd_text: str) -> float:
    """
    Compute cosine similarity between resume and JD embeddings.
    Returns a float in [0, 1]. Falls back to 0.5 if model unavailable.
    """
    model = _get_model()
    if model is None:
        return 0.5  # neutral fallback

    embeddings = model.encode([resume_text, jd_text], convert_to_numpy=True)
    sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return float(np.clip(sim, 0.0, 1.0))


def batch_semantic_scores(resumes: list[dict], jd_text: str) -> list[dict]:
    """
    Add 'semantic_score' (0–100) to each resume dict.
    Uses batch encoding for efficiency.
    """
    model = _get_model()
    if model is None:
        for r in resumes:
            r["semantic_score"] = 50.0
        return resumes

    texts = [r["raw_text"] for r in resumes]
    all_texts = texts + [jd_text]
    embeddings = model.encode(all_texts, convert_to_numpy=True, show_progress_bar=False)

    jd_emb = embeddings[-1]
    resume_embs = embeddings[:-1]

    for r, emb in zip(resumes, resume_embs):
        sim = cosine_similarity([emb], [jd_emb])[0][0]
        r["semantic_score"] = round(float(np.clip(sim, 0.0, 1.0)) * 100, 2)

    return resumes
