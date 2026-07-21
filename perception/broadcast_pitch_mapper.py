"""
MatchCast AI — Broadcast Pitch Mapping

Maps pixel coordinates to pitch space for moving broadcast cameras by detecting
the visible grass field region and normalizing positions within it.
Much more accurate than a fixed homography for panning broadcast footage.
"""

from __future__ import annotations

import cv2
import numpy as np


class BroadcastPitchMapper:
    """
    Detects the visible pitch (grass) region and maps feet positions into
    105m × 68m coordinates relative to that region.
    """

    PITCH_LENGTH = 105.0
    PITCH_WIDTH = 68.0

    def __init__(self, frame_width: int, frame_height: int):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self._bounds: tuple[float, float, float, float] | None = None  # x1,y1,x2,y2
        self._calibrated = False

    def calibrate_from_frame(self, frame: np.ndarray) -> bool:
        """Detect grass field bounds from a single frame."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # Green grass range (tuned for football pitches)
        mask1 = cv2.inRange(hsv, (25, 30, 30), (95, 255, 255))
        mask2 = cv2.inRange(hsv, (35, 20, 40), (85, 200, 200))
        mask = cv2.bitwise_or(mask1, mask2)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return self._fallback_bounds()

        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        frame_area = self.frame_width * self.frame_height
        if area < frame_area * 0.08:
            return self._fallback_bounds()

        x, y, w, h = cv2.boundingRect(largest)
        # Shrink slightly to avoid advertising boards
        pad_x = w * 0.02
        pad_y = h * 0.03
        x1 = max(0, x + pad_x)
        y1 = max(0, y + pad_y)
        x2 = min(self.frame_width, x + w - pad_x)
        y2 = min(self.frame_height, y + h - pad_y * 2)

        if x2 - x1 < 50 or y2 - y1 < 30:
            return self._fallback_bounds()

        self._bounds = (float(x1), float(y1), float(x2), float(y2))
        self._calibrated = True
        print(
            f"[PitchMapper] Field bounds: "
            f"({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f}) "
            f"from {self.frame_width}x{self.frame_height} frame"
        )
        return True

    def _fallback_bounds(self) -> bool:
        """Use center 85% of frame when grass detection fails."""
        mx = self.frame_width * 0.075
        my = self.frame_height * 0.12
        self._bounds = (
            mx,
            my,
            self.frame_width - mx,
            self.frame_height - my * 0.5,
        )
        self._calibrated = True
        print("[PitchMapper] Using fallback center-field bounds.")
        return True

    def transform_point(self, x: float, y: float) -> tuple[float, float]:
        """Map pixel (feet) position to pitch coordinates."""
        if not self._calibrated or self._bounds is None:
            px = (x / max(1, self.frame_width)) * self.PITCH_LENGTH
            py = (y / max(1, self.frame_height)) * self.PITCH_WIDTH
            return self._clamp(px, py)

        x1, y1, x2, y2 = self._bounds
        bw = max(1.0, x2 - x1)
        bh = max(1.0, y2 - y1)
        # Normalize within visible field, then scale to pitch
        nx = (x - x1) / bw
        ny = (y - y1) / bh
        px = nx * self.PITCH_LENGTH
        py = ny * self.PITCH_WIDTH
        return self._clamp(px, py)

    @staticmethod
    def _clamp(px: float, py: float) -> tuple[float, float]:
        return (
            max(0.0, min(BroadcastPitchMapper.PITCH_LENGTH, float(px))),
            max(0.0, min(BroadcastPitchMapper.PITCH_WIDTH, float(py))),
        )

    def transform_frame_players(
        self,
        feet_points: list[tuple[float, float]],
    ) -> list[tuple[float, float]]:
        """
        Optional per-frame refinement: spread players using cluster hull when
        many detections exist (keeps relative shape on tight broadcast crops).
        """
        if len(feet_points) < 6:
            return [self.transform_point(x, y) for x, y in feet_points]

        xs = [p[0] for p in feet_points]
        ys = [p[1] for p in feet_points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)

        # Blend global field map (70%) with within-frame spread (30%)
        out = []
        for x, y in feet_points:
            gx, gy = self.transform_point(x, y)
            lx = ((x - min_x) / span_x) * self.PITCH_LENGTH
            ly = ((y - min_y) / span_y) * self.PITCH_WIDTH
            px = 0.7 * gx + 0.3 * lx
            py = 0.7 * gy + 0.3 * ly
            out.append(self._clamp(px, py))
        return out
