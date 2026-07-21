"""
MatchCast AI — Phase 1.1 Visual Validation Script

Runs YOLOv8 detection on sample frames from a match video
and saves annotated images for manual review.

Usage:
    python run_detection_test.py

This is the MANDATORY visual validation step before proceeding.
"""

import sys
import cv2
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from perception.detector import PlayerDetector


def run_validation(video_path: str, model_path: str = "data/models/best.pt"):
    """Run detection on sample frames and save annotated images."""

    print("=" * 60)
    print("  MatchCast AI — Phase 1.1 Visual Validation")
    print("=" * 60)
    print(f"\n  Video:  {video_path}")
    print(f"  Model:  {model_path}")

    # Open video to get info
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"\n❌ ERROR: Cannot open video: {video_path}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total_frames / fps if fps > 0 else 0

    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps:.1f}")
    print(f"  Total frames: {total_frames}")
    print(f"  Duration: {duration/60:.1f} minutes")
    cap.release()

    # Initialize detector
    print(f"\n🔄 Loading YOLOv8 model...")
    detector = PlayerDetector(model_path=model_path, confidence_threshold=0.3)

    # Sample 8 frames spread across the video
    # Skip first/last 5% to avoid pre-game/post-game footage
    start_frame = int(total_frames * 0.05)
    end_frame = int(total_frames * 0.95)
    sample_frames = [
        int(start_frame + i * (end_frame - start_frame) / 9)
        for i in range(1, 9)
    ]

    # Output directory
    output_dir = Path("data/outputs/detection_validation")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🎯 Running detection on {len(sample_frames)} sample frames...")
    print(f"📁 Saving to: {output_dir}\n")

    saved_paths = detector.detect_video_sample(
        video_path=video_path,
        output_dir=str(output_dir),
        sample_frames=sample_frames,
    )

    # Summary
    print("\n" + "=" * 60)
    print("  ✅ VISUAL VALIDATION COMPLETE")
    print("=" * 60)
    print(f"\n  Annotated frames saved to: {output_dir}")
    print(f"  Files:")
    for p in saved_paths:
        print(f"    → {Path(p).name}")

    print(f"\n  ⚠️  REVIEW CHECKLIST:")
    print(f"  1. Are PLAYERS correctly boxed with green rectangles?")
    print(f"  2. Is the BALL detected (yellow box)?")
    print(f"  3. Are REFEREES distinguished (blue box)?")
    print(f"  4. Are GOALKEEPERS detected (red box)?")
    print(f"  5. Any false positives (crowd, ads, etc.)?")
    print(f"\n  Open the images in: {output_dir.resolve()}")
    print(f"  Then tell me if they look correct.\n")


if __name__ == "__main__":
    # Use the first uploaded video
    video_dir = Path("data/videos")
    video_files = list(video_dir.rglob("*.mp4"))

    if not video_files:
        print("❌ No video files found in data/videos/")
        print("   Upload a video through the frontend first, or place one manually.")
        sys.exit(1)

    # Use the first video found
    video_path = str(video_files[0])
    print(f"Found video: {video_path}")

    run_validation(video_path)
