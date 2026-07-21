"""
Optional jersey number extraction.

Uses pytesseract when available. Designed to be lightweight: samples once every
N frames per track and caches best results.
"""

from __future__ import annotations

import cv2
import numpy as np

try:
    import pytesseract
except Exception:
    pytesseract = None


class JerseyNumberExtractor:
    def __init__(self, enabled: bool = False, sample_interval: int = 12):
        self.enabled = enabled and (pytesseract is not None)
        self.sample_interval = max(1, int(sample_interval))
        self._best: dict[int, tuple[str, float]] = {}

    def _crop_back_region(self, frame: np.ndarray, bbox: np.ndarray) -> np.ndarray | None:
        x1, y1, x2, y2 = [int(v) for v in bbox]
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        bw, bh = x2 - x1, y2 - y1
        if bw < 16 or bh < 32:
            return None

        # Back-shirt center-upper region where numbers are most likely.
        rx1 = x1 + int(bw * 0.24)
        rx2 = x2 - int(bw * 0.24)
        ry1 = y1 + int(bh * 0.20)
        ry2 = y1 + int(bh * 0.62)
        if rx2 <= rx1 or ry2 <= ry1:
            return None
        return frame[ry1:ry2, rx1:rx2]

    @staticmethod
    def _prep(img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        up = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        _, th = cv2.threshold(up, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return th

    def _ocr_digits(self, prepared: np.ndarray) -> tuple[str | None, float]:
        if not self.enabled or pytesseract is None:
            return None, 0.0

        cfg = "--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789"
        text = pytesseract.image_to_string(prepared, config=cfg).strip()
        digits = "".join(ch for ch in text if ch.isdigit())
        if not digits:
            return None, 0.0
        if len(digits) > 2:
            digits = digits[:2]

        # Confidence proxy from fill ratio and length; not OCR-native confidence.
        non_zero = float(np.count_nonzero(prepared))
        ratio = non_zero / max(1.0, prepared.size)
        conf = min(1.0, 0.55 + 0.35 * (len(digits) / 2.0) + 0.10 * min(1.0, ratio * 2.0))
        return digits, conf

    def observe(
        self,
        frame: np.ndarray,
        bbox: np.ndarray,
        tracker_id: int,
        frame_idx: int,
    ) -> tuple[str | None, float | None]:
        if tracker_id < 0:
            return None, None

        if tracker_id in self._best:
            best_num, best_conf = self._best[tracker_id]
        else:
            best_num, best_conf = None, 0.0

        if (not self.enabled) or (frame_idx % self.sample_interval != 0):
            return best_num, (best_conf if best_num else None)

        crop = self._crop_back_region(frame, bbox)
        if crop is None:
            return best_num, (best_conf if best_num else None)

        prepared = self._prep(crop)
        digits, conf = self._ocr_digits(prepared)
        if digits is not None and conf >= best_conf:
            self._best[tracker_id] = (digits, conf)
            return digits, conf

        return best_num, (best_conf if best_num else None)
