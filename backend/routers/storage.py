"""
MatchCast AI — B2 Storage API Routes

Endpoints to upload match assets to Backblaze B2 and manage storage.
"""

import json
import threading
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from backend.config import settings
from backend.routers.matches import _matches

router = APIRouter()


# ---------------------------------------------------------------------------
# Job tracking
# ---------------------------------------------------------------------------

class StorageJobStatus(BaseModel):
    match_id: str
    phase: str       # "queued" | "uploading" | "complete" | "failed"
    progress: float
    message: str
    asset_count: int = 0
    total_size_bytes: int = 0
    errors: list[str] = []


_storage_jobs: Dict[str, StorageJobStatus] = {}
_storage_lock = threading.Lock()


def _run_upload(match_id: str, video_path: str, outputs_dir: str):
    """Background task: upload all match assets to B2."""
    def progress_cb(msg: str, progress: float):
        with _storage_lock:
            _storage_jobs[match_id] = StorageJobStatus(
                match_id=match_id,
                phase="uploading",
                progress=progress,
                message=msg,
            )

    try:
        from storage.b2 import upload_match_assets
        result = upload_match_assets(
            match_id=match_id,
            outputs_dir=outputs_dir,
            video_path=video_path,
            progress_callback=progress_cb,
        )

        with _storage_lock:
            phase = "complete"
            message = f"Uploaded {result['asset_count']} assets to B2."
            errors = result.get("errors", [])
            if result.get("status") == "skipped":
                phase = "failed"
                message = result.get("message", "B2 upload skipped.")
            elif result.get("status") in {"partial", "failed"} or errors:
                phase = "failed"
                message = result.get("message") or "B2 upload completed with errors."

            _storage_jobs[match_id] = StorageJobStatus(
                match_id=match_id,
                phase=phase,
                progress=1.0,
                message=message,
                asset_count=result["asset_count"],
                total_size_bytes=result["total_size_bytes"],
                errors=errors,
            )

    except Exception as e:
        print(f"[B2] Upload error for {match_id}: {e}")
        with _storage_lock:
            _storage_jobs[match_id] = StorageJobStatus(
                match_id=match_id,
                phase="failed",
                progress=0.0,
                message=f"Upload failed: {str(e)}",
                errors=[str(e)],
            )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/{match_id}/upload")
async def upload_to_b2(match_id: str, background_tasks: BackgroundTasks):
    """Upload all match assets to Backblaze B2."""
    if match_id not in _matches:
        raise HTTPException(status_code=404, detail="Match not found")

    from storage.b2 import storage_status as _b2_status_fn
    if not _b2_status_fn()["configured"]:
        raise HTTPException(
            status_code=400,
            detail="B2 credentials not configured. Add B2_APPLICATION_KEY_ID and B2_APPLICATION_KEY to .env.",
        )

    match_info = _matches[match_id]
    outputs_dir = str(settings.OUTPUTS_DIR / match_id)
    video_path = match_info.video_path or ""

    # Check if already running
    with _storage_lock:
        if match_id in _storage_jobs:
            job = _storage_jobs[match_id]
            if job.phase == "uploading":
                return {"match_id": match_id, "status": "already_running"}

    with _storage_lock:
        _storage_jobs[match_id] = StorageJobStatus(
            match_id=match_id,
            phase="queued",
            progress=0.0,
            message="Upload queued...",
        )

    background_tasks.add_task(_run_upload, match_id, video_path, outputs_dir)

    return {
        "match_id": match_id,
        "status": "queued",
        "message": "B2 upload started in the background.",
    }


@router.get("/{match_id}/upload-status")
async def get_upload_status(match_id: str):
    """Poll B2 upload progress."""
    with _storage_lock:
        if match_id in _storage_jobs:
            return _storage_jobs[match_id]

    return StorageJobStatus(
        match_id=match_id,
        phase="not_started",
        progress=0.0,
        message="No upload has been started for this match.",
    )


@router.get("/{match_id}/assets")
async def get_match_assets(match_id: str):
    """List all assets stored in B2 for a match."""
    from storage.b2 import storage_status as _b2_status_fn, list_match_assets
    if not _b2_status_fn()["configured"]:
        raise HTTPException(status_code=400, detail="B2 not configured.")

    try:
        assets = list_match_assets(match_id)
        return {"match_id": match_id, "assets": assets, "count": len(assets)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list assets: {str(e)}")


@router.get("/{match_id}/download-url")
async def get_asset_download_url(match_id: str, filename: str):
    """Get a pre-signed download URL for a B2 asset."""
    from storage.b2 import storage_status as _b2_status_fn, get_download_url
    if not _b2_status_fn()["configured"]:
        raise HTTPException(status_code=400, detail="B2 not configured.")

    try:
        url = get_download_url(match_id, filename)
        return {"match_id": match_id, "filename": filename, "url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get URL: {str(e)}")


@router.get("/status")
async def get_storage_status():
    """Check B2 storage configuration status."""
    from storage.b2 import storage_status
    return storage_status()
