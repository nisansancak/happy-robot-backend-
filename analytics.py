from fastapi import APIRouter

router = APIRouter()

# Mock DB — swap for a real Postgres query
_MOCK_STATS = {
    "language_requests": {"en": 142, "de": 87, "es": 34, "fr": 21},
    "voice_scores": {
        "female": {"count": 93, "avg_score": 3.8},
        "male":   {"count": 49, "avg_score": 3.1},
    },
}

@router.get("/stats")
async def get_stats():
    """Which voice wins? What language dominates? Let the data drive."""
    stats = _MOCK_STATS
    top_language = max(stats["language_requests"], key=stats["language_requests"].get)
    best_voice   = max(stats["voice_scores"], key=lambda k: stats["voice_scores"][k]["avg_score"])

    return {
        **stats,
        "recommendations": {
            "default_language": top_language,
            "default_voice":    best_voice,
            "reason": f"{best_voice} voice scores {stats['voice_scores'][best_voice]['avg_score']:.1f}/5 avg",
        }
    }

@router.post("/record-call-outcome")
async def record_outcome(voice_gender: str, language: str, score: int):
    """Called after every hang-up. Feeds the A/B test loop."""
    # In prod: INSERT INTO call_outcomes VALUES (...)
    return {"recorded": True, "voice": voice_gender, "lang": language, "score": score}
