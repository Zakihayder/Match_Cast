"""
MatchCast AI — Backblaze B2 storage (scaffold).

Intended design: store per match, under a consistent key structure, the raw
video, the event dataset (CSV/JSON), the Genblaze provenance manifest, generated
commentary/audio/graphics, and the final highlight reel — e.g.
    matches/{match_id}/raw.mp4
    matches/{match_id}/events.csv
    matches/{match_id}/manifest.json
    matches/{match_id}/reel.mp4

Storing the provenance manifest is direct evidence for the hackathon's
"B2 storage + data orchestration" criterion, so it is not optional.

This module is a scaffold: the interface is defined; actual uploads are not
implemented until B2 credentials + a client (Genblaze S3StorageBackend or boto3)
are wired in.
"""

try:
    from matchcast_settings import b2_configured, B2_BUCKET_NAME
except Exception:  # pragma: no cover
    def b2_configured() -> bool:
        return False

    B2_BUCKET_NAME = "matchcast-assets"


def storage_status() -> dict:
    """Report whether B2 storage can run."""
    configured = b2_configured()
    return {
        "configured": configured,
        "implemented": False,
        "bucket": B2_BUCKET_NAME,
        "message": (
            f"B2 credentials detected — target bucket '{B2_BUCKET_NAME}'. "
            "Upload implementation pending."
            if configured
            else "No B2 credentials found in .env. Add B2_APPLICATION_KEY_ID and "
            "B2_APPLICATION_KEY to enable storage + provenance."
        ),
    }


def match_key(match_id: str, filename: str) -> str:
    """Return the canonical B2 object key for a match asset."""
    return f"matches/{match_id}/{filename}"


class B2Storage:
    """Thin B2 storage client (scaffold)."""

    def __init__(self) -> None:
        self.status = storage_status()

    def upload(self, local_path: str, match_id: str, filename: str) -> str:
        """Upload one asset and return its B2 key. Not implemented yet."""
        raise NotImplementedError(
            "B2 upload is not implemented yet. It will use Genblaze's "
            "S3StorageBackend.for_backblaze() (or boto3) once credentials exist."
        )
