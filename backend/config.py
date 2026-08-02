"""
MatchCast AI — Application Configuration

Loads environment variables with sensible defaults.
External service configuration is handled gracefully when values are absent.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """Central config — reads from env vars, falls back to defaults."""

    # --- Genblaze / GMI Cloud ---
    GENBLAZE_API_KEY: str = os.getenv("GENBLAZE_API_KEY", "")
    GMI_CLOUD_API_KEY: str = os.getenv("GMI_CLOUD_API_KEY", "")

    # --- Backblaze B2 ---
    B2_APPLICATION_KEY_ID: str = os.getenv("B2_APPLICATION_KEY_ID", "")
    B2_APPLICATION_KEY: str = os.getenv("B2_APPLICATION_KEY", "")
    B2_BUCKET_NAME: str = os.getenv("B2_BUCKET_NAME", "matchcast-assets")

    # --- App ---
    FASTAPI_HOST: str = os.getenv("FASTAPI_HOST", "0.0.0.0")
    FASTAPI_PORT: int = int(os.getenv("FASTAPI_PORT", "8000"))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")

    # --- Model Paths ---
    YOLO_MODEL_PATH: str = os.getenv("YOLO_MODEL_PATH", "data/models/best.pt")
    YOLO_FALLBACK_MODEL: str = os.getenv("YOLO_FALLBACK_MODEL", "yolov8n.pt")

    # --- Processing ---
    MAX_VIDEO_DURATION: int = int(os.getenv("MAX_VIDEO_DURATION", "600"))
    FRAME_SAMPLE_RATE: int = int(os.getenv("FRAME_SAMPLE_RATE", "2"))
    # Analyze 1 of every N frames. On CPU keep this high (e.g. 12-25); on a
    # GPU you can lower it. Set via PROCESSING_FRAME_STRIDE in .env.
    PROCESSING_FRAME_STRIDE: int = int(os.getenv("PROCESSING_FRAME_STRIDE", "12"))
    # Optional cap on frames processed (None = whole video).
    PROCESSING_FRAME_LIMIT: int | None = (
        int(os.getenv("PROCESSING_FRAME_LIMIT"))
        if os.getenv("PROCESSING_FRAME_LIMIT")
        else None
    )

    # --- Static camera mode (whole field visible) ---
    STATIC_CAMERA_MODE: bool = os.getenv("STATIC_CAMERA_MODE", "false").lower() in {
        "1", "true", "yes", "on"
    }
    # Format: "x1,y1;x2,y2;x3,y3;x4,y4" (TL, TR, BR, BL)
    STATIC_CAMERA_SRC_POINTS: str = os.getenv("STATIC_CAMERA_SRC_POINTS", "")

    # --- Optional jersey-number extraction (OCR) ---
    JERSEY_OCR_ENABLED: bool = os.getenv("JERSEY_OCR_ENABLED", "false").lower() in {
        "1", "true", "yes", "on"
    }
    JERSEY_OCR_INTERVAL: int = int(os.getenv("JERSEY_OCR_INTERVAL", "12"))

    # --- Paths ---
    DATA_DIR: Path = PROJECT_ROOT / "data"
    VIDEOS_DIR: Path = DATA_DIR / "videos"
    OUTPUTS_DIR: Path = DATA_DIR / "outputs"
    MODELS_DIR: Path = DATA_DIR / "models"

    def __init__(self):
        # Ensure data directories exist
        self.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def yolo_model_resolved(self) -> str:
        """Return fine-tuned model path if it exists, otherwise fallback."""
        fine_tuned = PROJECT_ROOT / self.YOLO_MODEL_PATH
        if fine_tuned.exists():
            return str(fine_tuned)
        return self.YOLO_FALLBACK_MODEL  # ultralytics auto-downloads pretrained


settings = Settings()
