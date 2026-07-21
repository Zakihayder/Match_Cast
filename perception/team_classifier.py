"""
MatchCast AI — Team Classification via Jersey Color

Assigns Team A / Team B from jersey colors using k-means on torso crops.
Works on broadcast footage without manual labels.
"""

from __future__ import annotations

import cv2
import numpy as np
from collections import defaultdict


class TeamClassifier:
    """
    Learns two jersey-color clusters from early frames, then assigns stable
    team labels (A/B) to each tracker ID.
    """

    MIN_SAMPLES_TO_CLUSTER = 40
    MIN_OBSERVATIONS = 8  # min frames before trusting an ID's team

    def __init__(self):
        self._color_samples: list[np.ndarray] = []
        self._id_samples: dict[int, list[np.ndarray]] = defaultdict(list)
        self._id_team: dict[int, str] = {}
        self._cluster_centers: np.ndarray | None = None
        self._cluster_to_team: dict[int, str] = {}
        self._frames_seen = 0

    def _torso_color(self, frame: np.ndarray, bbox: np.ndarray) -> np.ndarray | None:
        """Median LAB color of the jersey torso region inside a bbox."""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 - x1 < 6 or y2 - y1 < 10:
            return None

        crop_h = y2 - y1
        crop_w = x2 - x1
        # Upper torso — avoids shorts/grass at feet
        ty1 = y1 + int(crop_h * 0.12)
        ty2 = y1 + int(crop_h * 0.55)
        tx1 = x1 + int(crop_w * 0.20)
        tx2 = x2 - int(crop_w * 0.20)
        if tx2 <= tx1 or ty2 <= ty1:
            return None

        torso = frame[ty1:ty2, tx1:tx2]
        if torso.size == 0:
            return None

        lab = cv2.cvtColor(torso, cv2.COLOR_BGR2LAB)
        # Flatten and remove very dark (shadows) and very bright (highlights)
        pixels = lab.reshape(-1, 3).astype(np.float32)
        l = pixels[:, 0]
        mask = (l > 25) & (l < 245)
        if mask.sum() < 10:
            return np.median(pixels, axis=0)
        return np.median(pixels[mask], axis=0)

    def _fit_clusters(self) -> None:
        if len(self._color_samples) < self.MIN_SAMPLES_TO_CLUSTER:
            return
        data = np.array(self._color_samples, dtype=np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
        _, labels, centers = cv2.kmeans(
            data, 2, None, criteria, 3, cv2.KMEANS_PP_CENTERS
        )
        self._cluster_centers = centers
        # Team with lighter jerseys (higher L*) → A by convention
        if centers[0][0] >= centers[1][0]:
            self._cluster_to_team = {0: "A", 1: "B"}
        else:
            self._cluster_to_team = {0: "B", 1: "A"}

        # Assign all collected ID samples
        for tid, samples in self._id_samples.items():
            if tid in self._id_team:
                continue
            if len(samples) >= self.MIN_OBSERVATIONS:
                self._assign_id_from_samples(tid, samples)

        print(
            f"[TeamClassifier] Clusters ready from {len(data)} samples. "
            f"Assigned {len(self._id_team)} player IDs."
        )

    def _assign_id_from_samples(self, tracker_id: int, samples: list[np.ndarray]) -> None:
        if self._cluster_centers is None:
            return
        avg = np.mean(samples, axis=0)
        dists = [float(np.linalg.norm(avg - c)) for c in self._cluster_centers]
        cluster = int(np.argmin(dists))
        self._id_team[tracker_id] = self._cluster_to_team.get(cluster, "A")

    def observe(
        self,
        frame: np.ndarray,
        bbox: np.ndarray,
        tracker_id: int,
        class_name: str,
    ) -> str | None:
        """
        Record a color sample and return team if known.
        Returns None for referees; A/B once classified.
        """
        if class_name == "referee":
            return "R"
        if class_name == "goalkeeper":
            # Goalkeepers classified by color like outfield players
            pass

        self._frames_seen += 1
        color = self._torso_color(frame, bbox)
        if color is None:
            return self._id_team.get(tracker_id)

        if tracker_id not in self._id_team:
            self._color_samples.append(color)
            self._id_samples[tracker_id].append(color)
            if (
                self._cluster_centers is None
                and len(self._color_samples) >= self.MIN_SAMPLES_TO_CLUSTER
            ):
                self._fit_clusters()
            elif self._cluster_centers is not None and len(self._id_samples[tracker_id]) >= self.MIN_OBSERVATIONS:
                self._assign_id_from_samples(tracker_id, self._id_samples[tracker_id])

        return self._id_team.get(tracker_id)

    def finalize(self) -> None:
        """Assign remaining IDs after the video pass."""
        if self._cluster_centers is None and len(self._color_samples) >= 20:
            self._fit_clusters()
        for tid, samples in self._id_samples.items():
            if tid not in self._id_team and len(samples) >= 3:
                self._assign_id_from_samples(tid, samples)

    def get_team(self, tracker_id: int, pitch_x: float | None = None) -> str:
        """Return team for an ID, with pitch-x fallback for unclassified IDs."""
        if tracker_id in self._id_team:
            return self._id_team[tracker_id]
        if pitch_x is not None:
            return "A" if pitch_x < 52.5 else "B"
        return "A" if tracker_id % 2 == 0 else "B"
