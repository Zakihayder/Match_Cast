"""
MatchCast AI — Tracking Output Verifier

Quick sanity check for a perception `tracking.json`. Prints data-level health
metrics so you can trust (or debug) the results before viewing them in the app.

Usage:
    python scripts/verify_tracking.py path/to/tracking.json
"""

import json
import statistics
import sys
from collections import Counter


def verify(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)

    frames = d.get("frames", [])
    print("=== META ===")
    for k in ("match_id", "video_filename", "fps", "total_frames",
              "duration_seconds", "pitch_dimensions"):
        print(f"  {k}: {d.get(k)}")
    print(f"  frames in file: {len(frames)}")

    players_per_frame = []
    teams = Counter()
    ids = set()
    ball_frames = 0
    xs, ys = [], []

    for fr in frames:
        players = fr.get("players", [])
        players_per_frame.append(len(players))
        if fr.get("ball"):
            ball_frames += 1
        for pl in players:
            teams[pl.get("team", "other")] += 1
            ids.add(pl.get("id"))
            xs.append(pl.get("pitch_x"))
            ys.append(pl.get("pitch_y"))

    print("\n=== PLAYERS ===")
    if players_per_frame:
        print(f"  players/frame: min={min(players_per_frame)} "
              f"max={max(players_per_frame)} "
              f"avg={statistics.mean(players_per_frame):.1f} "
              f"median={statistics.median(players_per_frame)}")
    print(f"  unique track IDs: {len(ids)}")
    print(f"  team split (detections): {dict(teams)}")

    print("\n=== BALL ===")
    pct = 100 * ball_frames / max(1, len(frames))
    print(f"  frames with ball: {ball_frames}/{len(frames)} ({pct:.1f}%)")

    print("\n=== PITCH COORDS (expect x in 0-105, y in 0-68) ===")
    if xs:
        print(f"  pitch_x: min={min(xs):.1f} max={max(xs):.1f}")
        print(f"  pitch_y: min={min(ys):.1f} max={max(ys):.1f}")
        in_x = sum(1 for v in xs if 0 <= v <= 105) / len(xs) * 100
        in_y = sum(1 for v in ys if 0 <= v <= 68) / len(ys) * 100
        print(f"  within pitch bounds: x={in_x:.1f}%  y={in_y:.1f}%")

    print("\n=== VERDICT ===")
    issues = []
    if players_per_frame and statistics.median(players_per_frame) < 10:
        issues.append("Low player count/frame (<10) — detector may be missing players.")
    if len(ids) > 200:
        issues.append(f"Very many track IDs ({len(ids)}) — tracker likely fragmenting identities.")
    if pct < 5:
        issues.append("Ball almost never detected — ball metrics/possession will be unreliable.")
    if xs:
        if in_x < 80 or in_y < 80:
            issues.append("Many positions fall outside the pitch — homography/calibration is off.")
    if not issues:
        print("  Looks healthy at the data level.")
    else:
        for i in issues:
            print(f"  [!] {i}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_tracking.py path/to/tracking.json")
        sys.exit(1)
    verify(sys.argv[1])
