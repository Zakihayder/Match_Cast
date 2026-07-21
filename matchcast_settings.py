"""
MatchCast AI — Shared settings / credential loader.

Reads API credentials from the repo-root .env (if python-dotenv is available)
and exposes small helpers used by the generative / intelligence / storage layers
and the Streamlit pages to report whether each integration is configured.

Nothing here calls an external service — it only reports configuration state.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# .env loading is best-effort: the app still runs (in "not configured" mode)
# even if python-dotenv is not installed.
try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except Exception:
    pass


# --- Genblaze / GMI Cloud (generative pipeline) ---
GENBLAZE_API_KEY = os.getenv("GENBLAZE_API_KEY", "")
GMI_CLOUD_API_KEY = os.getenv("GMI_CLOUD_API_KEY", "")

# --- Backblaze B2 (storage + provenance) ---
B2_APPLICATION_KEY_ID = os.getenv("B2_APPLICATION_KEY_ID", "")
B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY", "")
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME", "matchcast-assets")


def genblaze_configured() -> bool:
    """True if at least one generative provider key is present."""
    return bool(GENBLAZE_API_KEY or GMI_CLOUD_API_KEY)


def b2_configured() -> bool:
    """True if both B2 credential halves are present."""
    return bool(B2_APPLICATION_KEY_ID and B2_APPLICATION_KEY)
