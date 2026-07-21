"""
MatchCast AI — Player & Ball Detection (Phase 1, Step 1.1)

YOLOv8-based detection for football players and ball.

Workflow:
  1. Fine-tune YOLOv8 on Colab (see notebooks/yolov8_finetune.py)
  2. Export best.pt → data/models/best.pt
  3. This module loads the model and runs inference

Visual validation is REQUIRED before trusting any metrics.
Use `detect_and_visualize()` to overlay boxes on frames for review.
"""

import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
    print("[WARNING] ultralytics not installed. Detection will not work.")

try:
    import supervision as sv
except ImportError:
    sv = None
    print("[WARNING] supervision not installed. Annotation helpers unavailable.")


# YOLO class IDs for a football detection model
# These will be updated based on the actual fine-tuned model's class mapping
FOOTBALL_CLASSES = {
    0: "player",
    1: "ball",
    2: "referee",
    3: "goalkeeper",
}


@dataclass
class Detection:
    """Single detection result."""
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    confidence: float
    class_id: int
    class_name: str

    @property
    def center(self) -> tuple[float, float]:
        """Bottom-center point (feet position, better for pitch mapping)."""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, y2)


class PlayerDetector:
    """
    YOLOv8-based player and ball detector.
    
    Usage:
        detector = PlayerDetector("data/models/best.pt")
        detections = detector.detect_frame(frame)
        annotated = detector.detect_and_visualize(frame)  # for visual validation
    """

    def __init__(self, model_path: str = None, confidence_threshold: float = 0.3, inference_size: int = 640):
        """
        Initialize the detector.
        
        Args:
            model_path: Path to .pt weights. If None, uses config defaults.
            confidence_threshold: Minimum confidence to keep a detection.
            inference_size: YOLO inference size (416 is faster on CPU).
        """
        if YOLO is None:
            raise ImportError(
                "ultralytics is required. Install with: pip install ultralytics"
            )

        if model_path is None:
            from backend.config import settings
            model_path = settings.yolo_model_resolved

        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.inference_size = inference_size
        self.class_names = self.model.names  # Use model's own class mapping

        print(f"[Detector] Loaded model: {model_path}")
        print(f"[Detector] Classes: {self.class_names}")
        print(f"[Detector] Confidence: {confidence_threshold}, imgsz: {inference_size}")

    def predict(self, frame: np.ndarray):
        """Run YOLO inference and return the first result."""
        return self.model(
            frame,
            conf=self.confidence_threshold,
            imgsz=self.inference_size,
            verbose=False,
        )[0]

    def detect_frame(self, frame: np.ndarray) -> list[Detection]:
        """
        Run detection on a single frame.
        
        Args:
            frame: BGR image (OpenCV format).
            
        Returns:
            List of Detection objects.
        """
        results = self.predict(frame)
        detections = []

        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = self.class_names.get(cls_id, f"class_{cls_id}")

            detections.append(Detection(
                bbox=(float(x1), float(y1), float(x2), float(y2)),
                confidence=conf,
                class_id=cls_id,
                class_name=cls_name,
            ))

        return detections

    def detect_and_visualize(
        self,
        frame: np.ndarray,
        output_path: str = None,
    ) -> np.ndarray:
        """
        Run detection and overlay bounding boxes on the frame.
        
        This is the VISUAL VALIDATION step — use this to eyeball results
        before trusting any metrics.
        
        Args:
            frame: BGR image.
            output_path: If provided, saves annotated frame to this path.
            
        Returns:
            Annotated BGR image with boxes, labels, and confidence scores.
        """
        detections = self.detect_frame(frame)
        annotated = frame.copy()

        # Color scheme: players=green, ball=yellow, referee=blue, goalkeeper=red
        colors = {
            "player": (0, 255, 100),
            "ball": (0, 255, 255),
            "referee": (255, 150, 0),
            "goalkeeper": (0, 0, 255),
        }

        for det in detections:
            x1, y1, x2, y2 = [int(c) for c in det.bbox]
            color = colors.get(det.class_name, (200, 200, 200))

            # Draw bbox
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Draw label
            label = f"{det.class_name} {det.confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            cv2.rectangle(
                annotated,
                (x1, y1 - label_size[1] - 8),
                (x1 + label_size[0] + 4, y1),
                color,
                -1,
            )
            cv2.putText(
                annotated, label, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1,
            )

            # Draw center point (feet position)
            cx, cy = det.center
            cv2.circle(annotated, (int(cx), int(cy)), 4, color, -1)

        # Summary text
        player_count = sum(1 for d in detections if d.class_name in ("player", "goalkeeper"))
        ball_found = any(d.class_name == "ball" for d in detections)
        summary = f"Players: {player_count} | Ball: {'YES' if ball_found else 'NO'}"
        cv2.putText(
            annotated, summary, (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 100), 2,
        )

        if output_path:
            cv2.imwrite(output_path, annotated)
            print(f"[Detector] Saved annotated frame: {output_path}")

        return annotated

    def detect_video_sample(
        self,
        video_path: str,
        output_dir: str,
        sample_frames: list[int] = None,
        num_samples: int = 5,
    ) -> list[str]:
        """
        Run detection on sample frames from a video and save annotated images.
        
        This is the FIRST validation step — run this and eyeball the results
        before trusting metrics or proceeding to tracking.
        
        Args:
            video_path: Path to match video.
            output_dir: Directory to save annotated frames.
            sample_frames: Specific frame numbers. If None, samples evenly.
            num_samples: Number of evenly-spaced samples if sample_frames is None.
            
        Returns:
            List of paths to saved annotated frame images.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        if sample_frames is None:
            # Evenly space samples across the video
            sample_frames = [
                int(i * total_frames / (num_samples + 1))
                for i in range(1, num_samples + 1)
            ]

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        saved_paths = []

        print(f"[Detector] Video: {video_path}")
        print(f"[Detector] Total frames: {total_frames}, FPS: {fps:.1f}")
        print(f"[Detector] Sampling frames: {sample_frames}")

        for frame_num in sample_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if not ret:
                print(f"[Detector] WARNING: Could not read frame {frame_num}")
                continue

            timestamp = frame_num / fps
            out_file = str(output_path / f"detection_frame{frame_num}_t{timestamp:.1f}s.jpg")
            self.detect_and_visualize(frame, output_path=out_file)
            saved_paths.append(out_file)

        cap.release()
        print(f"[Detector] Saved {len(saved_paths)} annotated frames to {output_dir}")
        return saved_paths


def quick_test(video_path: str, model_path: str = None):
    """
    Quick test function — run from command line:
      python -m perception.detector --video path/to/clip.mp4
    
    Detects on 5 sample frames and saves annotated images.
    """
    detector = PlayerDetector(model_path)
    output_dir = str(Path(video_path).parent / "detection_test")
    paths = detector.detect_video_sample(video_path, output_dir)
    print(f"\n=== VISUAL VALIDATION REQUIRED ===")
    print(f"Check the annotated frames in: {output_dir}")
    print(f"Files: {paths}")
    print(f"Do the bounding boxes look correct? Are players/ball detected accurately?")
    return paths


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MatchCast AI — Player Detection Test")
    parser.add_argument("--video", required=True, help="Path to match video clip")
    parser.add_argument("--model", default=None, help="Path to YOLO .pt model weights")
    args = parser.parse_args()
    quick_test(args.video, args.model)
