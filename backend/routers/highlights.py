"""
MatchCast AI — Highlight Generation API Routes

Endpoints to generate, poll, and retrieve highlight reels + commentary.
"""

import json
import threading
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.config import settings
from backend.routers.matches import _matches

router = APIRouter()


# ---------------------------------------------------------------------------
# Job tracking
# ---------------------------------------------------------------------------

class HighlightJobStatus(BaseModel):
    match_id: str
    phase: str       # "queued" | "selecting_events" | "generating_commentary" | ... | "complete" | "failed"
    progress: float  # 0.0 to 1.0
    message: str
    commentary_mode: str = ""
    tts_mode: str = ""
    event_count: int = 0
    reel_available: bool = False
    error: str | None = None


_highlight_jobs: Dict[str, HighlightJobStatus] = {}
_highlight_lock = threading.Lock()


def _run_highlight_pipeline(match_id: str, video_path: str):
    """Background task: run the full highlight generation pipeline."""
    output_dir = str(settings.OUTPUTS_DIR / match_id / "highlights")

    def progress_cb(phase: str, progress: float):
        phase_messages = {
            "selecting_events": "Selecting key match moments...",
            "generating_commentary": "Generating match commentary...",
            "synthesizing_audio": "Synthesizing voiceover audio...",
            "cutting_clips": "Cutting highlight clips with FFmpeg...",
            "assembling_reel": "Assembling final highlight reel...",
            "complete": "Highlight generation complete!",
        }
        with _highlight_lock:
            _highlight_jobs[match_id] = HighlightJobStatus(
                match_id=match_id,
                phase=phase,
                progress=progress,
                message=phase_messages.get(phase, f"Processing: {phase}..."),
            )

    try:
        from perception.analytics import GameAnalyzer
        from generative.pipeline import HighlightPipeline

        # Load tracking + run analytics
        tracking_json = settings.OUTPUTS_DIR / match_id / "tracking.json"
        with open(tracking_json, "r") as f:
            tracking_data = json.load(f)

        analyzer = GameAnalyzer(tracking_data)
        report = analyzer.analyze()
        analytics_dict = report.model_dump()

        _pipeline = HighlightPipeline()
        result = _pipeline.generate(
            analytics=analytics_dict,
            video_path=video_path,
            output_dir=output_dir,
            progress_callback=progress_cb,
        )

        with _highlight_lock:
            _highlight_jobs[match_id] = HighlightJobStatus(
                match_id=match_id,
                phase="complete" if not result.error or result.commentary else "failed",
                progress=1.0,
                message=result.error or "Highlights generated successfully!",
                commentary_mode=result.commentary_mode,
                tts_mode=result.tts_mode,
                event_count=result.event_count,
                reel_available=result.reel_path is not None and Path(result.reel_path).exists(),
                error=result.error if not result.commentary else None,
            )

    except Exception as e:
        print(f"[Highlights] Pipeline error for {match_id}: {e}")
        with _highlight_lock:
            _highlight_jobs[match_id] = HighlightJobStatus(
                match_id=match_id,
                phase="failed",
                progress=0.0,
                message=f"Error: {str(e)}",
                error=str(e),
            )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/{match_id}/generate")
async def generate_highlights(match_id: str, background_tasks: BackgroundTasks):
    """Trigger highlight reel generation for a completed match."""
    if match_id not in _matches:
        raise HTTPException(status_code=404, detail="Match not found")

    match_info = _matches[match_id]
    if match_info.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Match must be fully processed before generating highlights."
        )

    target_id = "colab_match_01" if match_id == "demo-match" else match_id
    tracking_json = settings.OUTPUTS_DIR / target_id / "tracking.json"
    if not tracking_json.exists():
        raise HTTPException(status_code=400, detail="No tracking data found.")

    # Check if already running
    with _highlight_lock:
        if match_id in _highlight_jobs:
            job = _highlight_jobs[match_id]
            if job.phase not in ("complete", "failed"):
                return {
                    "match_id": match_id,
                    "status": "already_running",
                    "message": "Highlight generation is already in progress.",
                }

    # Queue the job
    with _highlight_lock:
        _highlight_jobs[match_id] = HighlightJobStatus(
            match_id=match_id,
            phase="queued",
            progress=0.0,
            message="Highlight generation queued...",
        )

    video_path = match_info.video_path or ""
    background_tasks.add_task(_run_highlight_pipeline, match_id, video_path)

    return {
        "match_id": match_id,
        "status": "queued",
        "message": "Highlight generation started in the background.",
    }


@router.get("/{match_id}/status")
async def get_highlight_status(match_id: str):
    """Poll highlight generation progress."""
    # Check if highlights already exist on disk even without a job
    target_id = "colab_match_01" if match_id == "demo-match" else match_id
    highlight_dir = settings.OUTPUTS_DIR / target_id / "highlights"
    commentary_file = highlight_dir / "commentary.json"

    with _highlight_lock:
        if match_id in _highlight_jobs:
            return _highlight_jobs[match_id]

    # If commentary exists from a previous run (server restart), report complete
    if commentary_file.exists():
        reel_path = highlight_dir / "highlight_reel.mp4"
        return HighlightJobStatus(
            match_id=match_id,
            phase="complete",
            progress=1.0,
            message="Highlights available (from previous generation).",
            reel_available=reel_path.exists(),
        )

    return HighlightJobStatus(
        match_id=match_id,
        phase="not_started",
        progress=0.0,
        message="No highlight generation has been started for this match.",
    )


@router.get("/{match_id}/commentary")
async def get_commentary(match_id: str):
    """Retrieve generated commentary for a match."""
    target_id = "colab_match_01" if match_id == "demo-match" else match_id
    commentary_file = settings.OUTPUTS_DIR / target_id / "highlights" / "commentary.json"
    if not commentary_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Commentary not yet generated. Trigger generation first."
        )

    with open(commentary_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {"match_id": match_id, "commentary": data}


@router.get("/{match_id}/reel")
async def get_highlight_reel(match_id: str):
    """Download the generated highlight reel MP4."""
    target_id = "colab_match_01" if match_id == "demo-match" else match_id
    reel_path = settings.OUTPUTS_DIR / target_id / "highlights" / "highlight_reel.mp4"
    if not reel_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Highlight reel not available. Either not generated yet or FFmpeg was not available."
        )

    return FileResponse(
        path=str(reel_path),
        media_type="video/mp4",
        filename=f"matchcast_highlights_{match_id}.mp4",
    )


@router.get("/pipeline-status")
async def get_pipeline_status():
    """Check generative pipeline configuration status."""
    from generative.pipeline import pipeline_status
    return pipeline_status()
