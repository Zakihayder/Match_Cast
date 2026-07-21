"""
Static-camera pitch mapper for full-field views.

Uses one fixed homography for the full video. If source points are not
provided, the full frame corners are mapped to the pitch corners.
"""

from __future__ import annotations

import cv2
import numpy as np


class StaticPitchMapper:
    PITCH_LENGTH = 105.0
    PITCH_WIDTH = 68.0

    def __init__(
        self,
        frame_width: int,
        frame_height: int,
        source_points: list[tuple[float, float]] | None = None,
    ):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.source_points = source_points or [
            (0.0, 0.0),
            (float(frame_width), 0.0),
            (float(frame_width), float(frame_height)),
            (0.0, float(frame_height)),
        ]
        self._homography: np.ndarray | None = None

    def calibrate_once(self) -> bool:
        if len(self.source_points) != 4:
            return False

        src = np.array(self.source_points, dtype=np.float32)
        dst = np.array(
            [
                [0.0, 0.0],
                [self.PITCH_LENGTH, 0.0],
                [self.PITCH_LENGTH, self.PITCH_WIDTH],
                [0.0, self.PITCH_WIDTH],
            ],
            dtype=np.float32,
        )
        self._homography = cv2.getPerspectiveTransform(src, dst)
        return True

    def transform_point(self, x: float, y: float) -> tuple[float, float]:
        if self._homography is None:
            nx = (x / max(1.0, float(self.frame_width))) * self.PITCH_LENGTH
            ny = (y / max(1.0, float(self.frame_height))) * self.PITCH_WIDTH
            return self._clamp(nx, ny)

        src = np.array([[[float(x), float(y)]]], dtype=np.float32)
        out = cv2.perspectiveTransform(src, self._homography)[0][0]
        return self._clamp(float(out[0]), float(out[1]))

    def transform_frame_players(
        self,
        feet_points: list[tuple[float, float]],
    ) -> list[tuple[float, float]]:
        return [self.transform_point(x, y) for x, y in feet_points]

    @staticmethod
    def _clamp(px: float, py: float) -> tuple[float, float]:
        return (
            max(0.0, min(StaticPitchMapper.PITCH_LENGTH, float(px))),
            max(0.0, min(StaticPitchMapper.PITCH_WIDTH, float(py))),
        )
