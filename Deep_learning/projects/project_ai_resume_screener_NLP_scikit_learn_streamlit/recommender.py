"""
recommender.py — Composite Scoring & Candidate Ranking
Combines skill match score + semantic similarity into a final ranked list.
"""

from typing import Optional


# Weighting constants (must sum to 1.0)
SKILL_WEIGHT    = 0.40
SEMANTIC_WEIGHT = 0.60

EXPERIENCE_BONUS = 2.0   # bonus points per year of relevant experience (capped)
MAX_EXP_BONUS    = 10.0  # maximum bonus from experience


def experience_bonus(candidate_years: Optional[float], required_years: Optional[float]) -> float:
    """
    Small bonus for experience. If JD requires N years and candidate has ≥ N,
    award proportional bonus (capped at MAX_EXP_BONUS).
    """
    if candidate_years is None:
        return 0.0
    if required_years is None:
        # No JD requirement — give partial bonus for experience
        return min(candidate_years * 0.5, MAX_EXP_BONUS / 2)
    if candidate_years >= required_years:
        return min((candidate_years - required_years + 1) * EXPERIENCE_BONUS, MAX_EXP_BONUS)
    # Candidate has less than required — small partial credit
    ratio = candidate_years / required_years
    return round(ratio * (MAX_EXP_BONUS / 2), 2)


def compute_final_score(
    skill_score: float,
    semantic_score: float,
    years_exp: Optional[float] = None,
    years_required: Optional[float] = None,
) -> float:
    """
    Composite score formula:
        base   = 0.40 × skill_score + 0.60 × semantic_score   (out of 100)
        bonus  = experience_bonus (0–10 pts)
        final  = min(base + bonus, 100)
    """
    base  = (SKILL_WEIGHT * skill_score) + (SEMANTIC_WEIGHT * semantic_score)
    bonus = experience_bonus(years_exp, years_required)
    return round(min(base + bonus, 100.0), 2)


def rank_candidates(candidates: list[dict], jd_parsed: dict) -> list[dict]:
    """
    Given a list of candidate dicts (already enriched with skill_score and
    semantic_score), compute final scores and return sorted list (best first).

    Each candidate dict is expected to have:
        raw_text, name, email, years_exp,
        skill_score, semantic_score,
        matched_skills, missing_skills, candidate_skills
    """
    years_required = jd_parsed.get("years_required")

    for c in candidates:
        c["final_score"] = compute_final_score(
            skill_score    = c.get("skill_score", 0),
            semantic_score = c.get("semantic_score", 0),
            years_exp      = c.get("years_exp"),
            years_required = years_required,
        )
        c["recommendation"] = _label(c["final_score"])

    ranked = sorted(candidates, key=lambda x: x["final_score"], reverse=True)

    # Assign rank
    for i, c in enumerate(ranked, 1):
        c["rank"] = i

    return ranked


def _label(score: float) -> str:
    """Human-readable recommendation label based on final score."""
    if score >= 80:
        return "🟢 Highly Recommended"
    elif score >= 60:
        return "🟡 Recommended"
    elif score >= 40:
        return "🟠 Consider"
    else:
        return "🔴 Not Recommended"


def summarise_ranking(ranked: list[dict]) -> dict:
    """Return aggregate stats for the ranked candidate list."""
    scores = [c["final_score"] for c in ranked]
    return {
        "total":     len(ranked),
        "top_score": max(scores) if scores else 0,
        "avg_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "highly_recommended": sum(1 for c in ranked if c["final_score"] >= 80),
        "recommended":        sum(1 for c in ranked if 60 <= c["final_score"] < 80),
        "consider":           sum(1 for c in ranked if 40 <= c["final_score"] < 60),
        "not_recommended":    sum(1 for c in ranked if c["final_score"] < 40),
    }
