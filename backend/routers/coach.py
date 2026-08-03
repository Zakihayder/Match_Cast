"""
MatchCast AI — AI Coach API Routes

Endpoints for AI Coach tactical recommendations grounded in match analytics.
"""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.routers.matches import _matches
from perception.analytics import GameAnalyzer
from intelligence.coach import AICoach

router = APIRouter()

# Shared coach instance (stateless, safe to reuse)
_coach = AICoach()


@router.get("/{match_id}/coach")
async def get_coach_recommendations(match_id: str):
    """
    Generate AI Coach tactical recommendations for a match.
    Uses LLM when API key is configured, falls back to heuristic engine.
    Every recommendation cites the concrete stats behind it.
    """
    if match_id not in _matches:
        raise HTTPException(status_code=404, detail="Match not found")

    target_id = "colab_match_01" if match_id == "demo-match" else match_id
    tracking_json = settings.OUTPUTS_DIR / target_id / "tracking.json"
    if not tracking_json.exists():
        raise HTTPException(
            status_code=400,
            detail="Match tracking data is not yet available. Run perception pipeline first."
        )

    try:
        with open(tracking_json, "r") as f:
            data = json.load(f)

        analyzer = GameAnalyzer(data)
        report = analyzer.analyze()
        analytics_dict = report.model_dump()

        result = _coach.recommend(analytics_dict)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate coach recommendations: {str(e)}"
        )


@router.get("/status")
async def get_coach_status():
    """Check AI Coach configuration status."""
    return _coach.status
