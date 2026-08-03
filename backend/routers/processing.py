"""
MatchCast AI — Video Processing Routes

Endpoints to trigger and monitor the perception pipeline.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import asyncio
from typing import Dict

from backend.config import settings
from backend.routers.matches import _matches

router = APIRouter()


class ProcessingStatus(BaseModel):
    """Status of a match processing job."""
    match_id: str
    phase: str  # "uploaded" | "detection" | "tracking" | "calibration" | "complete" | "failed"
    progress: float  # 0.0 to 1.0
    message: str


# Global dictionary to keep track of active processing job status
# Key: match_id, Value: ProcessingStatus
_processing_jobs: Dict[str, ProcessingStatus] = {}


def run_pipeline_bg(match_id: str, video_path: str):
    """Background task to run the perception pipeline."""
    try:
        # Update status to running
        _processing_jobs[match_id] = ProcessingStatus(
            match_id=match_id,
            phase="detection",
            progress=0.0,
            message="Loading YOLOv8 model and initializing tracker..."
        )
        
        # Update match status in the matches repository
        if match_id in _matches:
            _matches[match_id].status = "processing"
            
        from perception.pipeline import PerceptionPipeline
        src_points = PerceptionPipeline._parse_static_points(settings.STATIC_CAMERA_SRC_POINTS)
        pipeline = PerceptionPipeline(
            static_camera_mode=settings.STATIC_CAMERA_MODE,
            static_camera_src_points=src_points,
            jersey_ocr_enabled=settings.JERSEY_OCR_ENABLED,
            jersey_ocr_interval=settings.JERSEY_OCR_INTERVAL,
        )
        
        def progress_callback(fraction: float):
            _processing_jobs[match_id] = ProcessingStatus(
                match_id=match_id,
                phase="tracking",
                progress=fraction,
                message=f"Running player detection and tracking: {int(fraction * 100)}%"
            )
            
        # Sample frames (config-driven) so processing finishes in a sane time.
        # On CPU a high stride is essential; on GPU it can be lowered.
        output_json = pipeline.process_video(
            video_path=video_path,
            match_id=match_id,
            limit_frames=settings.PROCESSING_FRAME_LIMIT,
            frame_stride=settings.PROCESSING_FRAME_STRIDE,
            progress_callback=progress_callback
        )
        
        # Complete
        _processing_jobs[match_id] = ProcessingStatus(
            match_id=match_id,
            phase="complete",
            progress=1.0,
            message="Match analysis completed successfully."
        )
        
        # Update match info
        if match_id in _matches:
            _matches[match_id].status = "completed"
            _matches[match_id].tracking_data_path = output_json
            
    except Exception as e:
        print(f"[Pipeline Error] Failed to process match {match_id}: {str(e)}")
        _processing_jobs[match_id] = ProcessingStatus(
            match_id=match_id,
            phase="failed",
            progress=0.0,
            message=f"Error: {str(e)}"
        )
        if match_id in _matches:
            _matches[match_id].status = "failed"


@router.post("/{match_id}/start")
async def start_processing(match_id: str, background_tasks: BackgroundTasks):
    """
    Kick off the perception pipeline for a match.
    Phase 1: Detection → Tracking → Calibration → Schema output.
    """
    if match_id not in _matches:
        raise HTTPException(status_code=404, detail="Match not found")
        
    match_info = _matches[match_id]
    if not match_info.video_path:
        raise HTTPException(status_code=400, detail="Match has no associated video file")
        
    # Check if already running/completed
    if match_id in _processing_jobs:
        status = _processing_jobs[match_id]
        if status.phase in ("detection", "tracking", "calibration"):
            return {
                "match_id": match_id,
                "status": "already_running",
                "message": "Processing is already in progress."
            }
            
    # Add to background tasks
    background_tasks.add_task(run_pipeline_bg, match_id, match_info.video_path)
    
    _processing_jobs[match_id] = ProcessingStatus(
        match_id=match_id,
        phase="pending",
        progress=0.0,
        message="Queued video processing job..."
    )
    
    return {
        "match_id": match_id,
        "status": "queued",
        "message": "Processing pipeline started in the background."
    }


@router.get("/{match_id}/status", response_model=ProcessingStatus)
async def get_processing_status(match_id: str):
    """
    Poll processing status for a match.
    """
    if match_id not in _processing_jobs:
        # Fallback check if it was uploaded but not started
        if match_id in _matches:
            return ProcessingStatus(
                match_id=match_id,
                phase="uploaded",
                progress=0.0,
                message="Video uploaded. Ready to start analysis."
            )
        raise HTTPException(status_code=404, detail="Processing job not found")
        
    return _processing_jobs[match_id]
