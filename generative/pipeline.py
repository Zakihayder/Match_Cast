"""
MatchCast AI — Generative Pipeline (Phase 3, scaffold).

Intended design: ONE chained Genblaze pipeline
    commentary (text)  ->  voiceover (TTS)  ->  tactical graphic (image)
grounded in the real event data produced by the ClipMaker spine, with the
resulting provenance manifest + assets stored in Backblaze B2.

This module is currently a scaffold: the interface is defined so the
Highlight Studio page and future code can depend on a stable contract, but the
actual Genblaze calls are not implemented yet (raise NotImplementedError until
credentials + the Genblaze SDK are wired in).
"""

from dataclasses import dataclass, field
from typing import Any

try:
    from matchcast_settings import genblaze_configured
except Exception:  # pragma: no cover - import fallback when run outside repo root
    def genblaze_configured() -> bool:
        return False


@dataclass
class CommentaryLine:
    """A single data-grounded commentary line tied to one match event."""
    timestamp: float
    text: str
    audio_path: str | None = None
    graphic_path: str | None = None
    source_event: dict[str, Any] = field(default_factory=dict)


def pipeline_status() -> dict:
    """Report whether the generative pipeline can run."""
    configured = genblaze_configured()
    return {
        "configured": configured,
        "implemented": False,
        "message": (
            "Genblaze credentials detected — pipeline implementation pending."
            if configured
            else "No Genblaze/GMI Cloud key found in .env. Add GMI_CLOUD_API_KEY "
            "or GENBLAZE_API_KEY to enable generative commentary/TTS/graphics."
        ),
    }


class HighlightPipeline:
    """Chained Genblaze pipeline: text -> audio -> image (scaffold)."""

    def __init__(self) -> None:
        self.status = pipeline_status()

    def generate_commentary(self, events: list[dict]) -> list[CommentaryLine]:
        """Turn grounded event rows into commentary lines. Not implemented yet."""
        raise NotImplementedError(
            "Genblaze commentary generation is not implemented yet. "
            "This will build one text step per event, grounded in real data."
        )

    def synthesize_voiceover(self, lines: list[CommentaryLine]) -> list[CommentaryLine]:
        """Chain commentary text into a TTS step. Not implemented yet."""
        raise NotImplementedError(
            "TTS voiceover step is not implemented yet. "
            "A text-only fallback will be provided when it is."
        )

    def render_tactical_graphics(self, lines: list[CommentaryLine]) -> list[CommentaryLine]:
        """Chain an image-generation step for formation/tactical shifts. Not implemented yet."""
        raise NotImplementedError(
            "Tactical graphic generation is not implemented yet."
        )
