"""
MatchCast AI — Match Management Routes

CRUD operations for matches: upload video, list matches, get match details.
"""

import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from backend.config import settings

router = APIRouter()


class MatchInfo(BaseModel):
    """Match metadata returned to the frontend."""
    match_id: str
    filename: str
    status: str  # "uploaded" | "processing" | "completed" | "failed"
    video_path: str | None = None
    tracking_data_path: str | None = None


# In-memory store for now — will move to DB/B2 metadata later
_matches: dict[str, MatchInfo] = {}


def scan_existing_videos():
    """Scan settings.VIDEOS_DIR for existing videos and populate the repository."""
    if not settings.VIDEOS_DIR.exists():
        return
    for match_dir in settings.VIDEOS_DIR.iterdir():
        if match_dir.is_dir():
            match_id = match_dir.name
            video_files = list(match_dir.glob("*.mp4")) + list(match_dir.glob("*.avi")) + list(match_dir.glob("*.mov"))
            if video_files:
                video_file = video_files[0]
                tracking_json = settings.OUTPUTS_DIR / match_id / "tracking.json"
                status = "completed" if tracking_json.exists() else "uploaded"
                _matches[match_id] = MatchInfo(
                    match_id=match_id,
                    filename=video_file.name,
                    status=status,
                    video_path=str(video_file),
                    tracking_data_path=str(tracking_json) if tracking_json.exists() else None
                )
                print(f"[Match Registry] Registered existing match: {match_id} (Status: {status})")


# Populate matches registry
scan_existing_videos()


@router.post("/upload", response_model=MatchInfo)
async def upload_match_video(file: UploadFile = File(...)):
    """
    Upload a match video file.
    Saves locally, creates a match record, returns match_id for tracking.
    """
    # Validate file type
    allowed_types = {"video/mp4", "video/avi", "video/quicktime", "video/x-msvideo"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Accepted: mp4, avi, mov",
        )

    match_id = str(uuid.uuid4())[:8]
    match_dir = settings.VIDEOS_DIR / match_id
    match_dir.mkdir(parents=True, exist_ok=True)

    video_path = match_dir / file.filename
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    match_info = MatchInfo(
        match_id=match_id,
        filename=file.filename,
        status="uploaded",
        video_path=str(video_path),
    )
    _matches[match_id] = match_info

    return match_info


@router.get("/", response_model=list[MatchInfo])
async def list_matches():
    """List all uploaded matches."""
    return list(_matches.values())


@router.get("/{match_id}", response_model=MatchInfo)
async def get_match(match_id: str):
    """Get details for a specific match."""
    if match_id not in _matches:
        raise HTTPException(status_code=404, detail="Match not found")
    return _matches[match_id]
