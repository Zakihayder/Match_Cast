"""
MatchCast AI — Homography / Pitch Calibration (Phase 1, Step 1.3)

Maps pixel coordinates from video frames to real 2D pitch coordinates (105m x 68m).
"""

import cv2
import numpy as np

class PitchCalibrator:
    """
    Computes homography and transforms camera view coordinates to top-down 2D pitch view.
    
    Standard pitch dimensions:
      - Length (X): 105 meters (0 to 105)
      - Width (Y): 68 meters (0 to 68)
      - Center spot: (52.5, 34.0)
    """
    def __init__(self, src_pts: list[tuple[float, float]] = None, dst_pts: list[tuple[float, float]] = None):
        """
        Initialize the calibrator. If source and destination points are provided,
        computes the homography matrix immediately.
        
        Args:
            src_pts: List of 4+ points in pixel coordinates [(x, y), ...]
            dst_pts: List of 4+ corresponding points in pitch coordinates [(X, Y), ...]
        """
        self.H = None
        self.src_pts = np.array(src_pts, dtype=np.float32) if src_pts is not None else None
        self.dst_pts = np.array(dst_pts, dtype=np.float32) if dst_pts is not None else None
        
        if self.src_pts is not None and self.dst_pts is not None:
            self.compute_homography()
            
    def compute_homography(self):
        """Compute the homography matrix from source and destination points."""
        if len(self.src_pts) < 4 or len(self.dst_pts) < 4:
            raise ValueError("At least 4 reference point pairs are required for homography.")
            
        self.H, _ = cv2.findHomography(self.src_pts, self.dst_pts)
        print("[Calibrator] Homography matrix successfully computed.")
        
    def transform_point(self, x: float, y: float) -> tuple[float, float]:
        """
        Transform a single pixel coordinate to pitch coordinates (meters).
        
        Args:
            x: Pixel x-coordinate.
            y: Pixel y-coordinate.
            
        Returns:
            Tuple of (pitch_x, pitch_y) in meters.
        """
        if self.H is None:
            # Fallback to normalized coordinate mapping if homography is not configured
            # Assume center is center, and map margins roughly
            # Let's map 640x360 screen space to 105x68 pitch space
            pitch_x = (x / 640.0) * 105.0
            pitch_y = (y / 360.0) * 68.0
            return pitch_x, pitch_y
            
        point = np.array([[[x, y]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point, self.H)
        px, py = transformed[0][0]
        
        # Clamp coordinates to pitch boundaries to prevent extreme outliers
        px = max(0.0, min(105.0, float(px)))
        py = max(0.0, min(68.0, float(py)))
        
        return px, py

    def get_default_calibration(self, video_width: int = 640, video_height: int = 360) -> 'PitchCalibrator':
        """
        Get a default calibrator with pre-configured reference points
        for the standard broadcast view of the center field.
        """
        # Let's define 4 key points on the screen mapping to the 105x68 pitch
        # For a standard center-field camera:
        # Point 1: Center circle top edge in pixel space
        # Point 2: Center circle bottom edge in pixel space
        # Point 3: Center spot
        # Point 4: Left midfield center line intersection
        # Let's map standard center circle and center line points
        src = [
            [video_width * 0.5, video_height * 0.3],   # Center line top
            [video_width * 0.5, video_height * 0.8],   # Center line bottom
            [video_width * 0.35, video_height * 0.5],  # Left center-circle edge
            [video_width * 0.65, video_height * 0.5],  # Right center-circle edge
        ]
        
        # Mapping to pitch space:
        # Center line top: (52.5, 5.0)
        # Center line bottom: (52.5, 63.0)
        # Left center-circle edge: (52.5 - 9.15, 34.0) = (43.35, 34.0)
        # Right center-circle edge: (52.5 + 9.15, 34.0) = (61.65, 34.0)
        dst = [
            [52.5, 5.0],
            [52.5, 63.0],
            [43.35, 34.0],
            [61.65, 34.0],
        ]
        
        return PitchCalibrator(src, dst)
