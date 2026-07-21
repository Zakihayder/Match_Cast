"""
MatchCast AI — ClipMaker FFmpeg Core
Ported from ClipMaker v1.2.3 (clipmaker_core.py) by B03GHB4L1.
Provides FFmpeg-based clip cutting and highlight reel assembly.
"""

import os
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple, Callable


# ─────────────────────────────────────────────────────────────────────────────
# FFmpeg helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_ffmpeg_binary() -> str:
    """Locate the FFmpeg binary on PATH or via moviepy fallback."""
    cmd = shutil.which("ffmpeg")
    if cmd:
        return cmd
    try:
        from moviepy.config import FFMPEG_BINARY  # type: ignore
        if os.path.exists(FFMPEG_BINARY):
            return FFMPEG_BINARY
    except Exception:
        pass
    raise RuntimeError(
        "FFmpeg not found. Install FFmpeg and ensure it is on your PATH. "
        "Windows: https://www.gyan.dev/ffmpeg/builds/"
    )


def get_video_duration(path: str, ffmpeg_bin: Optional[str] = None) -> float:
    """Return video duration in seconds using FFmpeg."""
    import re
    ffmpeg_bin = ffmpeg_bin or get_ffmpeg_binary()
    r = subprocess.run([ffmpeg_bin, "-i", path], capture_output=True, text=True)
    output = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", output)
    if not m:
        raise ValueError(f"Could not determine duration of {path!r}")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def source_has_audio(src_path: str, ffmpeg_bin: Optional[str] = None) -> bool:
    """Return True if the video file has at least one audio stream."""
    import re
    ffmpeg_bin = ffmpeg_bin or get_ffmpeg_binary()
    result = subprocess.run(
        [ffmpeg_bin, "-hide_banner", "-i", src_path],
        capture_output=True, text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return bool(re.search(r"Stream #\d+:\d+.*Audio:", output))


# ─────────────────────────────────────────────────────────────────────────────
# Single-clip cutter
# ─────────────────────────────────────────────────────────────────────────────

def cut_clip(
    src_path: str,
    start: float,
    end: float,
    out_path: str,
    crf: int = 20,
    preset: str = "veryfast",
    audio_bitrate: str = "128k",
    ffmpeg_bin: Optional[str] = None,
) -> None:
    """
    Cut a clip from `src_path` between [start, end] seconds and write to
    `out_path`. Always encodes to H.264 + AAC for reliable concatenation.
    If the source has no audio, a silent audio stream is added.
    """
    ffmpeg_bin = ffmpeg_bin or get_ffmpeg_binary()
    duration = max(0.0, end - start)
    if duration == 0:
        raise ValueError("Clip has zero duration.")

    has_audio = source_has_audio(src_path, ffmpeg_bin)
    crf_s = str(crf)

    if has_audio:
        cmd = [
            ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error", "-nostdin",
            "-ss", str(start),
            "-i", src_path,
            "-t", str(duration),
            "-map", "0:v:0", "-map", "0:a:0?",
            "-c:v", "libx264", "-preset", preset, "-crf", crf_s, "-threads", "0",
            "-c:a", "aac", "-b:a", audio_bitrate,
            "-avoid_negative_ts", "make_zero",
            out_path,
        ]
    else:
        cmd = [
            ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error", "-nostdin",
            "-ss", str(start),
            "-t", str(duration),
            "-i", src_path,
            "-f", "lavfi",
            "-t", str(duration),
            "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", preset, "-crf", crf_s, "-threads", "0",
            "-c:a", "aac", "-b:a", audio_bitrate,
            "-shortest",
            "-avoid_negative_ts", "make_zero",
            out_path,
        ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg clip error: {r.stderr[-500:]}")


# ─────────────────────────────────────────────────────────────────────────────
# Highlight reel assembler
# ─────────────────────────────────────────────────────────────────────────────

ClipSpec = Tuple[str, float, float]   # (src_path, start_sec, end_sec)


def build_highlight_reel(
    clip_specs: List[ClipSpec],
    out_path: str,
    crf: int = 20,
    preset: str = "veryfast",
    audio_bitrate: str = "128k",
    ffmpeg_bin: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """
    Cut each clip in `clip_specs` into a temp file then concatenate them all
    into a single MP4 highlight reel at `out_path`.

    progress_callback(done, total) is called after each clip is cut.
    """
    if not clip_specs:
        raise ValueError("No clips to assemble.")

    ffmpeg_bin = ffmpeg_bin or get_ffmpeg_binary()
    tmp_dir = tempfile.mkdtemp(prefix="matchcast_clips_")
    tmp_files: List[str] = []
    list_path: Optional[str] = None
    total = len(clip_specs)

    try:
        for i, (src, start, end) in enumerate(clip_specs, 1):
            tmp_path = os.path.join(tmp_dir, f"part_{i:04d}.mp4")
            cut_clip(
                src_path=src,
                start=start,
                end=end,
                out_path=tmp_path,
                crf=crf,
                preset=preset,
                audio_bitrate=audio_bitrate,
                ffmpeg_bin=ffmpeg_bin,
            )
            tmp_files.append(tmp_path)
            if progress_callback:
                progress_callback(i, total)

        # Write concat list
        list_path = os.path.join(tmp_dir, "concat.txt")
        with open(list_path, "w", encoding="utf-8") as f:
            for p in tmp_files:
                p_safe = p.replace(os.sep, "/")
                f.write(f"file '{p_safe}'\n")

        # Concatenate — stream copy since all clips are already H.264+AAC
        concat_cmd = [
            ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error", "-nostdin",
            "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            out_path,
        ]
        r = subprocess.run(concat_cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"FFmpeg concat error: {r.stderr[-500:]}")

    finally:
        for p in tmp_files:
            try:
                os.remove(p)
            except Exception:
                pass
        if list_path:
            try:
                os.remove(list_path)
            except Exception:
                pass
        try:
            os.rmdir(tmp_dir)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Individual clip batch cutter (parallel)
# ─────────────────────────────────────────────────────────────────────────────

def cut_individual_clips(
    clip_specs: List[ClipSpec],
    out_dir: str,
    labels: Optional[List[str]] = None,
    crf: int = 20,
    preset: str = "veryfast",
    audio_bitrate: str = "128k",
    ffmpeg_bin: Optional[str] = None,
    max_workers: int = 4,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[str]:
    """
    Cut each clip in `clip_specs` as a separate MP4 file inside `out_dir`.
    Returns list of output paths.
    """
    os.makedirs(out_dir, exist_ok=True)
    ffmpeg_bin = ffmpeg_bin or get_ffmpeg_binary()
    total = len(clip_specs)
    saved: List[str] = []
    done_count = [0]

    def _cut(args):
        i, src, start, end, label = args
        safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in (label or "clip"))[:40]
        filepath = os.path.join(out_dir, f"{i:02d}_{safe_label}.mp4")
        cut_clip(src, start, end, filepath, crf, preset, audio_bitrate, ffmpeg_bin)
        return filepath

    specs_with_meta = [
        (i, src, start, end, (labels[i - 1] if labels and i <= len(labels) else f"clip_{i}"))
        for i, (src, start, end) in enumerate(clip_specs, 1)
    ]

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_cut, spec): spec for spec in specs_with_meta}
        for fut in as_completed(futures):
            try:
                path = fut.result()
                saved.append(path)
            except Exception as exc:
                spec = futures[fut]
                print(f"[ClipMaker] ERROR on clip {spec[0]}: {exc}")
            done_count[0] += 1
            if progress_callback:
                progress_callback(done_count[0], total)

    return sorted(saved)


# ─────────────────────────────────────────────────────────────────────────────
# Event-window builder: turn event timestamps into (start, end) windows
# ─────────────────────────────────────────────────────────────────────────────

def build_clip_windows(
    timestamps: List[float],
    pre_buffer: float = 10.0,
    post_buffer: float = 10.0,
    merge_gap: float = 3.0,
) -> List[Tuple[float, float]]:
    """
    Convert a list of event timestamps (seconds) into merged clip windows.
    Nearby windows are merged if their gap is less than `merge_gap` seconds.
    """
    if not timestamps:
        return []

    windows = [(max(0.0, t - pre_buffer), t + post_buffer) for t in sorted(timestamps)]

    # Merge overlapping / nearby windows
    merged = [list(windows[0])]
    for start, end in windows[1:]:
        prev = merged[-1]
        if start <= prev[1] + merge_gap:
            prev[1] = max(prev[1], end)
        else:
            merged.append([start, end])

    return [tuple(w) for w in merged]  # type: ignore
