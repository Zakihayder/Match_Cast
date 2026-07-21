"""
Synthetic goal/assist validator for MatchCast analytics.

Creates a small fake tracking sequence for static-camera style play:
- Team A pass from player 8 to player 9
- Team A shot by player 9
- Ball crosses goal line => goal
- Assist should be attributed to player 8
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from perception.analytics import GameAnalyzer


def build_synthetic_tracking() -> dict:
    fps = 10.0
    frames = []

    # Base players stay visible.
    def players_for(frame_idx: int):
        return [
            {"id": 8, "team": "A", "pitch_x": 70.0, "pitch_y": 30.0},
            {"id": 9, "team": "A", "pitch_x": 82.0, "pitch_y": 33.0},
            {"id": 3, "team": "B", "pitch_x": 76.0, "pitch_y": 32.0},
            {"id": 5, "team": "B", "pitch_x": 88.0, "pitch_y": 34.0},
        ]

    for i in range(120):
        t = i / fps

        # Ball path:
        # 0-3s near player 8, 3-6s near player 9 (pass), 6-8s still near 9,
        # 8-9s fast shot to goal line.
        if t < 3.0:
            bx, by = 70.5, 30.0
        elif t < 6.0:
            bx, by = 82.3, 33.1
        elif t < 8.0:
            bx, by = 84.0, 33.2
        elif t < 9.0:
            # Fast linear movement to the right goal line.
            prog = (t - 8.0) / 1.0
            bx = 84.0 + prog * 20.5
            by = 33.2
        else:
            bx, by = 104.4, 33.2

        frames.append(
            {
                "frame": i,
                "timestamp": t,
                "players": players_for(i),
                "ball": {"pitch_x": bx, "pitch_y": by, "confidence": 0.95},
            }
        )

    return {
        "match_id": "synthetic_goal_assist",
        "video_filename": "synthetic.mp4",
        "fps": fps,
        "total_frames": len(frames),
        "duration_seconds": len(frames) / fps,
        "frames": frames,
    }


def main() -> None:
    data = build_synthetic_tracking()
    report = GameAnalyzer(data).analyze()

    goals = [e for e in report.events if e.type == "goal"]
    assists = [e for e in report.events if e.type == "assist"]

    print(
        f"events={len(report.events)} goals={len(goals)} assists={len(assists)} "
        f"score={report.score_a}-{report.score_b}"
    )
    if report.quality_flags:
        print("quality_flags:", report.quality_flags)
    for e in report.events:
        if e.type in {"shot", "goal", "assist", "possession_change"}:
            print(f"{e.timestamp:6.2f}s {e.type:18} team={e.team} player={e.player_id} :: {e.message}")

    assert len(goals) >= 1, "Expected at least one goal event"
    assert len(assists) >= 1, "Expected at least one assist event"
    assert report.score_a == 1 and report.score_b == 0, "Unexpected synthetic scoreboard"

    # Strong expectation for this synthetic setup.
    assert goals[0].team == "A", "Expected Team A goal"
    assert goals[0].player_id == 9, "Expected scorer Player 9"
    assert assists[0].player_id == 8, "Expected assist by Player 8"

    print("\nSynthetic goal/assist test passed.")


if __name__ == "__main__":
    main()
