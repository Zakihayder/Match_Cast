"""
Track ID stabilizer for static-camera scenes.

Maps volatile tracker IDs to stable canonical IDs using nearest-neighbor
association in pitch space with short memory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _TrackState:
    canonical_id: int
    team: str
    px: float
    py: float
    last_seen_frame: int


class TrackIdStabilizer:
    def __init__(self, max_distance_m: float = 4.5, max_gap_frames: int = 60):
        self.max_distance_m = max_distance_m
        self.max_gap_frames = max_gap_frames
        self._next_canonical = 1
        self._raw_to_canonical: dict[int, int] = {}
        self._states: dict[int, _TrackState] = {}

    def stabilize(
        self,
        raw_id: int,
        team: str,
        px: float,
        py: float,
        frame_idx: int,
    ) -> int:
        if raw_id < 0:
            return raw_id

        if raw_id in self._raw_to_canonical:
            cid = self._raw_to_canonical[raw_id]
            self._states[cid] = _TrackState(cid, team, px, py, frame_idx)
            return cid

        best_cid = None
        best_dist = None
        for cid, state in self._states.items():
            if team not in ("A", "B") or state.team == team:
                gap = frame_idx - state.last_seen_frame
                if gap < 0 or gap > self.max_gap_frames:
                    continue
                dx = state.px - px
                dy = state.py - py
                dist = (dx * dx + dy * dy) ** 0.5
                if dist <= self.max_distance_m and (best_dist is None or dist < best_dist):
                    best_dist = dist
                    best_cid = cid

        if best_cid is None:
            best_cid = self._next_canonical
            self._next_canonical += 1

        self._raw_to_canonical[raw_id] = best_cid
        self._states[best_cid] = _TrackState(best_cid, team, px, py, frame_idx)
        return best_cid

    def prune(self, frame_idx: int) -> None:
        stale = [
            cid
            for cid, state in self._states.items()
            if frame_idx - state.last_seen_frame > self.max_gap_frames
        ]
        if stale:
            stale_set = set(stale)
            for cid in stale:
                self._states.pop(cid, None)
            to_remove = [rid for rid, cid in self._raw_to_canonical.items() if cid in stale_set]
            for rid in to_remove:
                self._raw_to_canonical.pop(rid, None)
