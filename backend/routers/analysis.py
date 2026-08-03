"""
MatchCast AI — Phase 2 Analysis & Radar Replay Routes

Endpoints to retrieve analytics (events, formations, stats) and tracking data.
"""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.routers.matches import _matches

router = APIRouter()


@router.get("/{match_id}/analytics")
async def get_match_analytics(match_id: str):
    """
    Run analytics on the match tracking dataset.
    Detects sprints, possession changes, shots, and formations.
    """
    if match_id not in _matches:
        raise HTTPException(status_code=404, detail="Match not found")
        
    tracking_json = settings.OUTPUTS_DIR / match_id / "tracking.json"
    if not tracking_json.exists():
        raise HTTPException(
            status_code=400,
            detail="Match tracking data is not yet available. Run perception pipeline first."
        )
        
    try:
        with open(tracking_json, "r") as f:
            data = json.load(f)
            
        from perception.analytics import GameAnalyzer
        analyzer = GameAnalyzer(data)
        report = analyzer.analyze()
        return report.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze tracking data: {str(e)}")


@router.get("/{match_id}/tracking")
async def get_match_tracking_data(match_id: str):
    """
    Retrieve the entire tracking JSON file for the match.
    Used by the frontend to render the radar view replay.
    """
    if match_id not in _matches:
        raise HTTPException(status_code=404, detail="Match not found")
        
    tracking_json = settings.OUTPUTS_DIR / match_id / "tracking.json"
    if not tracking_json.exists():
        raise HTTPException(
            status_code=400,
            detail="Match tracking data is not yet available. Run perception pipeline first."
        )
        
    try:
        with open(tracking_json, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read tracking data: {str(e)}")
