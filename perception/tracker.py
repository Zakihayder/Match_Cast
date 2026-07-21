"""
MatchCast AI — Player Tracking (Phase 1, Step 1.2)

ByteTrack via supervision for persistent player IDs across frames.
"""

import numpy as np
import supervision as sv
from ultralytics.engine.results import Results


class PlayerTracker:
    """
    ByteTrack wrapper using supervision.
    Assigns persistent IDs to players, goalkeepers, and referees.
    Ball detections are passed through without tracking.
    """

    def __init__(
        self,
        class_names: dict[int, str] | None = None,
        static_mode: bool = False,
        track_thresh: float = 0.20,
        track_buffer: int = 90,
        match_thresh: float = 0.75,
    ):
        self.class_names = class_names or {}
        if static_mode:
            # Static camera allows longer memory and stricter matching.
            track_buffer = max(track_buffer, 180)
            match_thresh = max(match_thresh, 0.82)

        self.tracker = sv.ByteTrack(
            track_activation_threshold=track_thresh,
            lost_track_buffer=track_buffer,
            minimum_matching_threshold=match_thresh,
        )
        print(
            f"[Tracker] Initialized ByteTrack "
            f"(buffer={track_buffer}, thresh={track_thresh:.2f}, match={match_thresh:.2f})"
        )

    def _is_ball(self, class_id: int) -> bool:
        name = self.class_names.get(int(class_id), "").lower()
        return name == "ball"

    def update(self, results: Results) -> sv.Detections:
        detections = sv.Detections.from_ultralytics(results)

        if len(detections) == 0:
            return detections

        is_ball = np.array([self._is_ball(c) for c in detections.class_id])
        to_track = detections[~is_ball]
        balls = detections[is_ball]

        tracked = self.tracker.update_with_detections(to_track) if len(to_track) else to_track

        if len(balls) > 0:
            balls.tracker_id = np.array([-1] * len(balls))
            if len(tracked):
                return sv.Detections.merge([tracked, balls])
            return balls

        return tracked
