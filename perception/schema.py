"""
MatchCast AI — Output Schema (Phase 1.4 — LOCKED)

This schema is the contract between Phase 1 and all downstream phases.
DO NOT modify field names or types without explicit approval.

Every phase reads from this structure:
- Phase 2: Events, formations, radar replay
- Phase 3: Genblaze commentary/TTS/graphics
- Phase 4: AI Coach, player summaries
"""

from pydantic import BaseModel, Field


class PlayerPosition(BaseModel):
    """Single player position in a frame."""
    id: int = Field(..., description="Persistent player tracking ID (from ByteTrack)")
    team: str = Field(..., description="Team assignment: 'A' or 'B'")
    pitch_x: float = Field(..., description="X position in pitch coordinates (0-105 meters)")
    pitch_y: float = Field(..., description="Y position in pitch coordinates (0-68 meters)")
    bbox_x1: float | None = Field(None, description="Original bounding box x1 (pixels)")
    bbox_y1: float | None = Field(None, description="Original bounding box y1 (pixels)")
    bbox_x2: float | None = Field(None, description="Original bounding box x2 (pixels)")
    bbox_y2: float | None = Field(None, description="Original bounding box y2 (pixels)")
    confidence: float | None = Field(None, description="Detection confidence score")
    jersey_number: str | None = Field(None, description="Optional jersey number detected from back shirt OCR")
    jersey_number_confidence: float | None = Field(None, description="Confidence proxy for jersey number OCR")


class BallPosition(BaseModel):
    """Ball position in a frame."""
    pitch_x: float = Field(..., description="X position in pitch coordinates (0-105 meters)")
    pitch_y: float = Field(..., description="Y position in pitch coordinates (0-68 meters)")
    confidence: float | None = Field(None, description="Detection confidence score")


class FrameData(BaseModel):
    """
    Complete tracking data for a single frame.
    
    This is the fundamental unit — stored as a list of these per match.
    The schema is LOCKED as of Phase 1.4.
    """
    frame: int = Field(..., description="Frame number in the video")
    timestamp: float = Field(..., description="Timestamp in seconds from video start")
    players: list[PlayerPosition] = Field(default_factory=list)
    ball: BallPosition | None = Field(None, description="Ball position, None if not detected")


class MatchTrackingData(BaseModel):
    """
    Complete tracking dataset for a match.
    Stored as JSON per match: data/outputs/{match_id}/tracking.json
    """
    match_id: str
    video_filename: str
    fps: float
    total_frames: int
    duration_seconds: float
    pitch_dimensions: dict = Field(
        default={"length": 105.0, "width": 68.0, "unit": "meters"},
        description="Real-world pitch dimensions used for coordinate mapping",
    )
    frames: list[FrameData] = Field(default_factory=list)
