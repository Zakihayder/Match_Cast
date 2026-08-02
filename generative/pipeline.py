from __future__ import annotations

"""
MatchCast AI — Generative Pipeline (Phase 3).

Commentary generation + TTS voiceover + highlight reel assembly.

Supports two modes:
  1. LLM-powered commentary (when API key is available)
  2. Template-based commentary (always works, no external API needed)

TTS supports: edge-tts (async, high quality) → gTTS → pyttsx3 → text-only fallback.
Highlight reel uses the ClipMaker FFmpeg core for clip cutting + concat.
"""

import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Callable

try:
    from matchcast_settings import genblaze_configured, GMI_CLOUD_API_KEY, GENBLAZE_API_KEY
except Exception:
    def genblaze_configured() -> bool:
        return False
    GMI_CLOUD_API_KEY = ""
    GENBLAZE_API_KEY = ""

try:
    from genblaze_core import Pipeline
    from genblaze_core.models.enums import Modality, StepStatus
    from genblaze_gmicloud.audio import GMICloudAudioProvider
    from genblaze_gmicloud.chat import chat as gmicloud_chat
    GENBLAZE_SDK_AVAILABLE = True
except Exception:
    Pipeline = None  # type: ignore[assignment]
    Modality = None  # type: ignore[assignment]
    StepStatus = None  # type: ignore[assignment]
    GMICloudAudioProvider = None  # type: ignore[assignment]
    gmicloud_chat = None  # type: ignore[assignment]
    GENBLAZE_SDK_AVAILABLE = False


def _is_gmicloud_configured() -> bool:
    """True when GMICloud credentials and the Genblaze SDK are both available."""
    api_key = GMI_CLOUD_API_KEY or GENBLAZE_API_KEY or os.getenv("OPENAI_API_KEY", "")
    return bool(api_key and not api_key.startswith("your-") and GENBLAZE_SDK_AVAILABLE)


def _download_remote_asset(url: str, out_path: str) -> None:
    """Download a remote asset URL to a local file path."""
    try:
        import urllib.request
        urllib.request.urlretrieve(url, out_path)
    except Exception as e:
        raise RuntimeError(f"Failed to download remote asset {url}: {e}") from e


def _synthesize_gmicloud_tts(lines: list[CommentaryLine], out_dir: str) -> str | None:
    """Synthesize TTS using the GMICloud audio provider."""
    if not _is_gmicloud_configured() or Pipeline is None or GMICloudAudioProvider is None or Modality is None:
        return None

    api_key = GMI_CLOUD_API_KEY or GENBLAZE_API_KEY or os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("your-"):
        return None

    model = os.getenv("GMI_TTS_MODEL", "elevenlabs-tts-v3")
    voice = os.getenv("GMI_TTS_VOICE", "Rachel")
    try:
        provider = GMICloudAudioProvider(api_key=api_key)
        pipeline = Pipeline("matchcast-tts", chain=False, preflight=False)
        for line in lines:
            pipeline.step(
                provider,
                model=model,
                prompt=line.text,
                modality=Modality.AUDIO,
                params={"voice": voice},
            )

        result = pipeline.run(raise_on_failure=False, progress=False)
        any_downloaded = False
        for idx, step in enumerate(result.run.steps):
            if getattr(step, "status", None) != StepStatus.SUCCEEDED:
                continue
            if not getattr(step, "assets", None):
                continue
            asset = step.assets[0]
            url = getattr(asset, "url", None)
            if not url:
                continue
            suffix = Path(url).suffix or ".mp3"
            out_path = os.path.join(out_dir, f"commentary_{idx:03d}{suffix}")
            try:
                _download_remote_asset(url, out_path)
                lines[idx].audio_path = out_path
                any_downloaded = True
            except Exception as exc:
                print(f"[Generative] Failed to download GMICloud TTS asset: {exc}")

        return "gmicloud" if any_downloaded else None
    except Exception as e:
        print(f"[Generative] GMICloud TTS pipeline failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CommentaryLine:
    """A single commentary line tied to one match event."""
    timestamp: float
    text: str
    audio_path: str | None = None
    event_type: str = ""
    team: str | None = None
    source_event: dict[str, Any] = field(default_factory=dict)


@dataclass
class HighlightResult:
    """Result of the full highlight pipeline."""
    reel_path: str | None = None
    clips: list[str] = field(default_factory=list)
    commentary: list[dict] = field(default_factory=list)
    commentary_mode: str = "template"
    tts_mode: str = "none"
    duration_seconds: float = 0.0
    event_count: int = 0
    error: str | None = None


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def pipeline_status() -> dict:
    """Report whether the generative pipeline can run."""
    api_key = GMI_CLOUD_API_KEY or GENBLAZE_API_KEY or os.getenv("OPENAI_API_KEY", "")
    has_key = bool(api_key) and not api_key.startswith("your-")
    has_ffmpeg = shutil.which("ffmpeg") is not None
    tts_engine = _detect_tts_engine()
    sdk_ready = GENBLAZE_SDK_AVAILABLE and GMICloudAudioProvider is not None and Pipeline is not None

    return {
        "configured": has_key and sdk_ready,
        "implemented": True,
        "ffmpeg_available": has_ffmpeg,
        "tts_engine": tts_engine,
        "commentary_mode": "llm" if has_key else "template",
        "message": _build_status_message(has_key, has_ffmpeg, tts_engine, sdk_ready),
    }


def _build_status_message(has_key: bool, has_ffmpeg: bool, tts_engine: str, sdk_ready: bool) -> str:
    parts = []
    if has_key and sdk_ready:
        parts.append("Genblaze SDK and credentials detected - commentary and TTS integration enabled.")
    elif has_key and not sdk_ready:
        parts.append("LLM credentials are present; cloud commentary and audio support are optional runtime extensions.")
    else:
        parts.append("No LLM key found - using template commentary that remains grounded in match events.")
    if has_ffmpeg:
        parts.append("FFmpeg available - highlight reel assembly enabled.")
    else:
        parts.append("FFmpeg not found - commentary will be generated but video assembly disabled.")
    if tts_engine != "none":
        parts.append(f"TTS engine: {tts_engine}.")
    else:
        parts.append("No local TTS engine available - text-only commentary or remote audio generation.")
    return " ".join(parts)


def _detect_tts_engine() -> str:
    """Detect best available TTS engine."""
    try:
        import edge_tts  # noqa: F401
        return "edge-tts"
    except ImportError:
        pass
    try:
        from gtts import gTTS  # noqa: F401
        return "gtts"
    except ImportError:
        pass
    try:
        import pyttsx3  # noqa: F401
        return "pyttsx3"
    except ImportError:
        pass
    return "none"


# ---------------------------------------------------------------------------
# Template-based commentary (no LLM needed)
# ---------------------------------------------------------------------------

_COMMENTARY_TEMPLATES = {
    "goal": [
        "GOAL! {team} scores! What a moment in this match!",
        "The net ripples! {team} finds the back of the net!",
        "It's a goal for {team}! The crowd goes wild!",
    ],
    "shot": [
        "{team} with a dangerous shot! The ball flies towards the goal.",
        "A powerful strike from {team}! The keeper will need to be alert.",
        "{team} tests the opposition goalkeeper with a well-struck effort.",
    ],
    "assist": [
        "Brilliant setup play from {team}! What vision to find the scorer.",
        "A perfectly weighted pass creates the opportunity for {team}.",
    ],
    "sprint": [
        "Explosive pace from Player #{player_id} on {team}! Covering ground rapidly.",
        "A burst of speed from {team}'s Player #{player_id} — real intensity on display.",
    ],
    "possession_change": [
        "{team} wins the ball back in the {half} half.",
        "Turnover! {team} regains possession and looks to build.",
    ],
    "dribble": [
        "Skillful footwork from Player #{player_id}! {team} player beats the press.",
        "A clever dribble by {team}'s Player #{player_id} creates space.",
    ],
    "formation_shift": [
        "{team} adjusts their shape — a tactical shift that could change the momentum.",
        "The manager's hand is visible here as {team} reshapes their formation.",
    ],
}


def _generate_template_commentary(events: list[dict]) -> list[CommentaryLine]:
    """Generate commentary lines using templates grounded in real events."""
    import random
    lines = []

    for evt in events:
        etype = evt.get("type", "unknown")
        templates = _COMMENTARY_TEMPLATES.get(etype)
        if not templates:
            continue

        team = f"Team {evt.get('team', '?')}" if evt.get("team") else "A player"
        player_id = evt.get("player_id", "?")
        half = "attacking" if evt.get("details", {}).get("ball_x", 52.5) > 52.5 else "defensive"

        template = random.choice(templates)
        text = template.format(team=team, player_id=player_id, half=half)

        # Use original message as fallback context
        original = evt.get("message", "")
        if original and etype in ("goal", "shot"):
            text = f"{text} {original}"

        lines.append(CommentaryLine(
            timestamp=evt.get("timestamp", 0.0),
            text=text,
            event_type=etype,
            team=evt.get("team"),
            source_event=evt,
        ))

    return lines


def _generate_gmicloud_commentary(events: list[dict]) -> list[CommentaryLine] | None:
    """Generate commentary via the GMICloud chat wrapper when configured."""
    if gmicloud_chat is None or not _is_gmicloud_configured():
        return None

    api_key = GMI_CLOUD_API_KEY or GENBLAZE_API_KEY or os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("your-"):
        return None

    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    base_url = os.getenv("GMI_BASE_URL", "") or "https://api.gmi-serving.com/v1"

    slim_events = []
    for e in events:
        slim_events.append({
            "timestamp": e.get("timestamp"),
            "type": e.get("type"),
            "team": e.get("team"),
            "player_id": e.get("player_id"),
            "message": e.get("message", ""),
        })

    try:
        messages = [
            {"role": "system", "content": _COMMENTARY_SYSTEM},
            {
                "role": "user",
                "content": (
                    "Generate commentary for these match events:\n\n"
                    f"```json\n{json.dumps(slim_events, indent=2)}\n```"
                ),
            },
        ]

        response = gmicloud_chat(
            model,
            messages=messages,
            api_key=api_key,
            base_url=base_url,
            temperature=0.6,
            max_tokens=1200,
        )
        content = response.text
        if not content:
            return None

        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            content = json_match.group(1)

        parsed = json.loads(content.strip())
        if not isinstance(parsed, list):
            return None

        lines = []
        for item in parsed:
            lines.append(CommentaryLine(
                timestamp=float(item.get("timestamp", 0)),
                text=item.get("text", ""),
                event_type=item.get("event_type", ""),
            ))
        return lines if lines else None
    except Exception as e:
        print(f"[Generative] GMICloud commentary failed: {e}")
        return None


# ---------------------------------------------------------------------------
# LLM-powered commentary
# ---------------------------------------------------------------------------

_COMMENTARY_SYSTEM = """You are an enthusiastic, professional football commentator for MatchCast AI.
You receive a list of real match events extracted by computer vision.

RULES:
1. Write one punchy commentary line per event (15-30 words each).
2. Be vivid, energetic, and match the event intensity (goals > shots > possession changes).
3. Reference the team and player ID when available.
4. Output valid JSON: a list of objects with keys: "timestamp", "text", "event_type".
5. Do NOT invent events. Only comment on the provided events.
6. Keep the tone exciting but not over-the-top for minor events."""


def _generate_llm_commentary(events: list[dict]) -> list[CommentaryLine] | None:
    """Generate commentary via LLM. Returns None on failure."""
    if _generate_gmicloud_commentary is not None:
        commentary_lines = _generate_gmicloud_commentary(events)
        if commentary_lines:
            return commentary_lines

    api_key = GMI_CLOUD_API_KEY or GENBLAZE_API_KEY or os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("your-"):
        return None

    base_url = os.getenv("LLM_BASE_URL", "")
    if not base_url:
        if GMI_CLOUD_API_KEY and not GMI_CLOUD_API_KEY.startswith("your-"):
            base_url = "https://api.gmi.ai/v1"
        else:
            base_url = "https://api.openai.com/v1"

    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Only send key event fields to save tokens
    slim_events = []
    for e in events:
        slim_events.append({
            "timestamp": e.get("timestamp"),
            "type": e.get("type"),
            "team": e.get("team"),
            "player_id": e.get("player_id"),
            "message": e.get("message", ""),
        })

    try:
        import urllib.request
        payload = json.dumps({
            "model": model,
            "temperature": 0.6,
            "max_tokens": 2000,
            "messages": [
                {"role": "system", "content": _COMMENTARY_SYSTEM},
                {"role": "user", "content": (
                    "Generate commentary for these match events:\n\n"
                    f"```json\n{json.dumps(slim_events, indent=2)}\n```"
                )},
            ],
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        content = body["choices"][0]["message"]["content"]
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            content = json_match.group(1)

        parsed = json.loads(content.strip())
        if not isinstance(parsed, list):
            return None

        lines = []
        for item in parsed:
            lines.append(CommentaryLine(
                timestamp=float(item.get("timestamp", 0)),
                text=item.get("text", ""),
                event_type=item.get("event_type", ""),
            ))
        return lines if lines else None

    except Exception as e:
        print(f"[Generative] LLM commentary failed: {e}")
        return None


# ---------------------------------------------------------------------------
# TTS engine
# ---------------------------------------------------------------------------

def _synthesize_tts(lines: list[CommentaryLine], out_dir: str) -> str:
    """Synthesize TTS audio for commentary lines. Returns engine used."""
    engine = _detect_tts_engine()

    if engine == "edge-tts":
        return _tts_edge(lines, out_dir)
    elif engine == "gtts":
        return _tts_gtts(lines, out_dir)
    elif engine == "pyttsx3":
        return _tts_pyttsx3(lines, out_dir)

    gmicloud_mode = _synthesize_gmicloud_tts(lines, out_dir)
    if gmicloud_mode:
        return gmicloud_mode

    return "none"


def _tts_edge(lines: list[CommentaryLine], out_dir: str) -> str:
    """Use edge-tts (Microsoft) for high-quality async TTS."""
    import asyncio
    import edge_tts

    async def _run():
        for i, line in enumerate(lines):
            out_path = os.path.join(out_dir, f"commentary_{i:03d}.mp3")
            communicate = edge_tts.Communicate(
                line.text,
                voice="en-GB-RyanNeural",
                rate="+5%",
            )
            await communicate.save(out_path)
            line.audio_path = out_path

    asyncio.run(_run())
    return "edge-tts"


def _tts_gtts(lines: list[CommentaryLine], out_dir: str) -> str:
    """Use gTTS (Google) for TTS."""
    from gtts import gTTS

    for i, line in enumerate(lines):
        out_path = os.path.join(out_dir, f"commentary_{i:03d}.mp3")
        tts = gTTS(text=line.text, lang="en", tld="co.uk")
        tts.save(out_path)
        line.audio_path = out_path

    return "gtts"


def _tts_pyttsx3(lines: list[CommentaryLine], out_dir: str) -> str:
    """Use pyttsx3 (offline) for TTS."""
    import pyttsx3

    engine = pyttsx3.init()
    engine.setProperty("rate", 165)

    for i, line in enumerate(lines):
        out_path = os.path.join(out_dir, f"commentary_{i:03d}.mp3")
        engine.save_to_file(line.text, out_path)

    engine.runAndWait()

    for i, line in enumerate(lines):
        out_path = os.path.join(out_dir, f"commentary_{i:03d}.mp3")
        if os.path.exists(out_path):
            line.audio_path = out_path

    return "pyttsx3"


# ---------------------------------------------------------------------------
# Highlight clip window builder
# ---------------------------------------------------------------------------

# Event priority for highlight selection (higher = more important)
_EVENT_PRIORITY = {
    "goal": 100,
    "assist": 90,
    "shot": 70,
    "dribble": 40,
    "formation_shift": 30,
    "sprint": 20,
    "possession_change": 10,
}


def select_highlight_events(
    events: list[dict],
    max_events: int = 12,
    max_duration_sec: float = 180.0,
    pre_buffer: float = 8.0,
    post_buffer: float = 6.0,
) -> list[dict]:
    """Select the most important events for the highlight reel."""
    if not events:
        return []

    # Score and sort by priority
    scored = []
    for evt in events:
        priority = _EVENT_PRIORITY.get(evt.get("type", ""), 5)
        scored.append((priority, evt))
    scored.sort(key=lambda x: x[0], reverse=True)

    # Take top events up to max
    selected = [evt for _, evt in scored[:max_events]]
    # Re-sort chronologically
    selected.sort(key=lambda e: e.get("timestamp", 0))

    # Estimate total duration and trim if needed
    total_dur = len(selected) * (pre_buffer + post_buffer)
    while total_dur > max_duration_sec and len(selected) > 3:
        # Remove lowest-priority event
        min_pri = min(selected, key=lambda e: _EVENT_PRIORITY.get(e.get("type", ""), 5))
        selected.remove(min_pri)
        total_dur = len(selected) * (pre_buffer + post_buffer)

    return selected


def build_clip_windows_from_events(
    events: list[dict],
    video_duration: float = 600.0,
    pre_buffer: float = 8.0,
    post_buffer: float = 6.0,
    merge_gap: float = 2.0,
) -> list[tuple[float, float]]:
    """Convert events into merged clip windows."""
    if not events:
        return []

    windows = []
    for evt in events:
        t = evt.get("timestamp", 0.0)
        start = max(0.0, t - pre_buffer)
        end = min(video_duration, t + post_buffer)
        windows.append((start, end))

    windows.sort()

    # Merge overlapping
    merged = [list(windows[0])]
    for start, end in windows[1:]:
        prev = merged[-1]
        if start <= prev[1] + merge_gap:
            prev[1] = max(prev[1], end)
        else:
            merged.append([start, end])

    return [(s, e) for s, e in merged]


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

class HighlightPipeline:
    """Full highlight generation pipeline: commentary → TTS → clip assembly."""

    def __init__(self) -> None:
        self.status = pipeline_status()

    def generate(
        self,
        analytics: dict,
        video_path: str,
        output_dir: str,
        max_events: int = 12,
        max_duration_sec: float = 180.0,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> HighlightResult:
        """
        Run the full highlight pipeline:
        1. Select key events
        2. Generate commentary (LLM or template)
        3. Synthesize TTS audio (if engine available)
        4. Cut clips and assemble reel (if FFmpeg available)
        """
        result = HighlightResult()
        os.makedirs(output_dir, exist_ok=True)

        try:
            # --- Step 1: Select events ---
            if progress_callback:
                progress_callback("selecting_events", 0.1)

            events = analytics.get("events", [])
            highlight_events = select_highlight_events(
                events, max_events=max_events, max_duration_sec=max_duration_sec
            )
            result.event_count = len(highlight_events)

            if not highlight_events:
                result.error = "No events found in match analytics to generate highlights."
                return result

            # --- Step 2: Generate commentary ---
            if progress_callback:
                progress_callback("generating_commentary", 0.2)

            commentary_lines = None
            api_key = GMI_CLOUD_API_KEY or GENBLAZE_API_KEY or os.getenv("OPENAI_API_KEY", "")
            has_key = bool(api_key) and not api_key.startswith("your-")

            if has_key:
                commentary_lines = _generate_llm_commentary(highlight_events)
                if commentary_lines:
                    result.commentary_mode = "llm"

            if not commentary_lines:
                commentary_lines = _generate_template_commentary(highlight_events)
                result.commentary_mode = "template"

            # Save commentary JSON
            commentary_data = []
            for line in commentary_lines:
                commentary_data.append({
                    "timestamp": line.timestamp,
                    "text": line.text,
                    "event_type": line.event_type,
                    "team": line.team,
                })
            result.commentary = commentary_data

            commentary_json = os.path.join(output_dir, "commentary.json")
            with open(commentary_json, "w", encoding="utf-8") as f:
                json.dump(commentary_data, f, indent=2, ensure_ascii=False)

            # --- Step 3: TTS ---
            if progress_callback:
                progress_callback("synthesizing_audio", 0.4)

            tts_dir = os.path.join(output_dir, "tts")
            os.makedirs(tts_dir, exist_ok=True)
            result.tts_mode = _synthesize_tts(commentary_lines, tts_dir)

            # --- Step 4: Clip assembly (needs FFmpeg + video) ---
            if progress_callback:
                progress_callback("cutting_clips", 0.6)

            has_ffmpeg = shutil.which("ffmpeg") is not None
            video_exists = video_path and os.path.isfile(video_path)

            if has_ffmpeg and video_exists:
                from backend.clipmaker.core import (
                    build_highlight_reel,
                    cut_individual_clips,
                    get_video_duration,
                )

                try:
                    vid_duration = get_video_duration(video_path)
                except Exception:
                    vid_duration = 600.0

                windows = build_clip_windows_from_events(
                    highlight_events,
                    video_duration=vid_duration,
                )

                clip_specs = [(video_path, s, e) for s, e in windows]

                # Cut individual clips
                if progress_callback:
                    progress_callback("cutting_clips", 0.65)

                clips_dir = os.path.join(output_dir, "clips")
                labels = []
                for evt in highlight_events:
                    t = evt.get("type", "clip")
                    ts = evt.get("timestamp", 0)
                    labels.append(f"{t}_{ts:.0f}s")

                individual_clips = cut_individual_clips(
                    clip_specs=clip_specs,
                    out_dir=clips_dir,
                    labels=labels[:len(clip_specs)],
                    progress_callback=lambda done, total: (
                        progress_callback("cutting_clips", 0.65 + 0.15 * done / max(1, total))
                        if progress_callback else None
                    ),
                )
                result.clips = individual_clips

                # Assemble highlight reel
                if progress_callback:
                    progress_callback("assembling_reel", 0.85)

                reel_path = os.path.join(output_dir, "highlight_reel.mp4")
                build_highlight_reel(
                    clip_specs=clip_specs,
                    out_path=reel_path,
                    progress_callback=lambda done, total: (
                        progress_callback("assembling_reel", 0.85 + 0.1 * done / max(1, total))
                        if progress_callback else None
                    ),
                )
                result.reel_path = reel_path

                # Calculate duration
                try:
                    result.duration_seconds = get_video_duration(reel_path)
                except Exception:
                    result.duration_seconds = sum(e - s for s, e in windows)

            else:
                # No FFmpeg or no video — commentary-only mode
                if not has_ffmpeg:
                    result.error = (
                        "FFmpeg not found on PATH. Commentary was generated successfully "
                        "but video clip assembly is disabled. Install FFmpeg to enable "
                        "highlight reel generation."
                    )
                elif not video_exists:
                    result.error = (
                        "Source video file not found. Commentary was generated but clips "
                        "could not be cut."
                    )

            if progress_callback:
                progress_callback("complete", 1.0)

        except Exception as e:
            result.error = str(e)
            print(f"[Generative] Pipeline error: {e}")

        return result
