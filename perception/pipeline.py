"""
MatchCast AI — Perception Pipeline Orchestrator (Phases 1.2, 1.3, 1.4)

Detection → Tracking → Team classification → Broadcast pitch mapping → JSON.
"""

import os
import cv2
import json
import time
from pathlib import Path
from typing import Optional

from perception.detector import PlayerDetector
from perception.tracker import PlayerTracker
from perception.broadcast_pitch_mapper import BroadcastPitchMapper
from perception.static_pitch_mapper import StaticPitchMapper
from perception.team_classifier import TeamClassifier
from perception.id_stabilizer import TrackIdStabilizer
from perception.jersey_number import JerseyNumberExtractor
from perception.schema import MatchTrackingData, FrameData, PlayerPosition, BallPosition


class PerceptionPipeline:
    """Full perception pipeline with broadcast-aware mapping and jersey teams."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.30,
        inference_size: int = 416,
        static_camera_mode: bool = False,
        static_camera_src_points: list[tuple[float, float]] | None = None,
        jersey_ocr_enabled: bool = False,
        jersey_ocr_interval: int = 12,
    ):
        self.static_camera_mode = static_camera_mode
        self.static_camera_src_points = static_camera_src_points
        self.detector = PlayerDetector(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            inference_size=inference_size,
        )
        self.tracker = PlayerTracker(
            class_names=self.detector.class_names,
            static_mode=static_camera_mode,
        )
        self.team_classifier = TeamClassifier()
        self.pitch_mapper: BroadcastPitchMapper | None = None
        self.id_stabilizer = TrackIdStabilizer(
            max_distance_m=5.0 if static_camera_mode else 4.0,
            max_gap_frames=100 if static_camera_mode else 60,
        )
        self.jersey_extractor = JerseyNumberExtractor(
            enabled=jersey_ocr_enabled,
            sample_interval=jersey_ocr_interval,
        )
        self._calibrated = False

    @staticmethod
    def _parse_static_points(raw: str) -> list[tuple[float, float]] | None:
        if not raw.strip():
            return None
        points: list[tuple[float, float]] = []
        for token in raw.split(";"):
            token = token.strip()
            if not token:
                continue
            xy = token.split(",")
            if len(xy) != 2:
                continue
            try:
                points.append((float(xy[0].strip()), float(xy[1].strip())))
            except ValueError:
                continue
        if len(points) == 4:
            return points
        return None

    def process_video(
        self,
        video_path: str,
        match_id: str,
        output_dir: str = "data/outputs",
        limit_frames: Optional[int] = None,
        start_frame: int = 0,
        frame_stride: int = 1,
        progress_callback=None,
    ) -> str:
        frame_stride = max(1, int(frame_stride))
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS)) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = total_frames / fps if fps > 0 else 0.0

        if self.static_camera_mode:
            self.pitch_mapper = StaticPitchMapper(
                width,
                height,
                source_points=self.static_camera_src_points,
            )
            self._calibrated = self.pitch_mapper.calibrate_once()
        else:
            self.pitch_mapper = BroadcastPitchMapper(width, height)
        self.team_classifier = TeamClassifier()

        print(f"[Pipeline] Processing match {match_id}")
        if self.static_camera_mode:
            print("[Pipeline] Static camera mode: ON")
        print(f"[Pipeline] Video: {width}x{height}, {fps:.1f} fps, {duration_seconds/60:.1f} min")
        if limit_frames:
            print(f"[Pipeline] Limit: {limit_frames} analyzed frames from frame {start_frame}")
        if frame_stride > 1:
            print(f"[Pipeline] Stride: {frame_stride} (~{fps / frame_stride:.1f} analyzed fps)")

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frames_data: list[FrameData] = []
        frame_idx = start_frame
        processed_count = 0
        last_good_frame: FrameData | None = None
        t0 = time.time()

        while cap.isOpened():
            if (frame_idx - start_frame) % frame_stride != 0:
                if not cap.grab():
                    break
                frame_idx += 1
                continue

            ret, frame = cap.read()
            if not ret:
                break

            timestamp = frame_idx / fps

            # Calibrate pitch mapper from first good frame with grass
            if not self._calibrated and not self.static_camera_mode:
                self._calibrated = self.pitch_mapper.calibrate_from_frame(frame)

            results = self.detector.predict(frame)
            tracked = self.tracker.update(results)

            # Collect player feet for optional cluster mapping
            player_entries: list[dict] = []
            ball_pos = None

            for i in range(len(tracked)):
                cls_id = int(tracked.class_id[i])
                bbox = tracked.xyxy[i]
                tracker_id = (
                    int(tracked.tracker_id[i])
                    if tracked.tracker_id is not None
                    else -1
                )
                conf = (
                    float(tracked.confidence[i])
                    if tracked.confidence is not None
                    else 1.0
                )
                class_name = self.detector.class_names.get(cls_id, "unknown")

                if class_name == "ball":
                    cx = (bbox[0] + bbox[2]) / 2.0
                    cy = (bbox[1] + bbox[3]) / 2.0
                    bp_x, bp_y = self.pitch_mapper.transform_point(cx, cy)
                    ball_pos = BallPosition(pitch_x=bp_x, pitch_y=bp_y, confidence=conf)
                    continue

                if class_name not in ("player", "goalkeeper", "referee"):
                    continue

                feet_x = (bbox[0] + bbox[2]) / 2.0
                feet_y = bbox[3]

                team = self.team_classifier.observe(frame, bbox, tracker_id, class_name)

                player_entries.append({
                    "id": tracker_id,
                    "class_name": class_name,
                    "feet_x": feet_x,
                    "feet_y": feet_y,
                    "bbox": bbox,
                    "conf": conf,
                    "team": team,
                })

            # Map all player feet with cluster-aware spread
            if player_entries:
                feet = [(e["feet_x"], e["feet_y"]) for e in player_entries]
                pitch_coords = self.pitch_mapper.transform_frame_players(feet)
            else:
                pitch_coords = []

            players_list: list[PlayerPosition] = []
            for entry, (px, py) in zip(player_entries, pitch_coords):
                raw_tid = entry["id"]
                class_name = entry["class_name"]
                if entry["team"] == "R" or class_name == "referee":
                    team = "R"
                    tid = raw_tid
                else:
                    team = self.team_classifier.get_team(raw_tid, px)
                    tid = self.id_stabilizer.stabilize(
                        raw_id=raw_tid,
                        team=team,
                        px=px,
                        py=py,
                        frame_idx=frame_idx,
                    )

                jersey_number, jersey_conf = self.jersey_extractor.observe(
                    frame=frame,
                    bbox=entry["bbox"],
                    tracker_id=tid,
                    frame_idx=frame_idx,
                )

                players_list.append(PlayerPosition(
                    id=tid,
                    team=team,
                    pitch_x=px,
                    pitch_y=py,
                    bbox_x1=float(entry["bbox"][0]),
                    bbox_y1=float(entry["bbox"][1]),
                    bbox_x2=float(entry["bbox"][2]),
                    bbox_y2=float(entry["bbox"][3]),
                    confidence=entry["conf"],
                    jersey_number=jersey_number,
                    jersey_number_confidence=jersey_conf,
                ))

            self.id_stabilizer.prune(frame_idx)

            frame_data = FrameData(
                frame=frame_idx,
                timestamp=timestamp,
                players=players_list,
                ball=ball_pos,
            )

            # Gap fill: if empty frame, carry forward last positions briefly
            if not players_list and last_good_frame and (timestamp - last_good_frame.timestamp) < 0.6:
                frame_data = FrameData(
                    frame=frame_idx,
                    timestamp=timestamp,
                    players=last_good_frame.players,
                    ball=ball_pos or last_good_frame.ball,
                )
            elif players_list:
                last_good_frame = frame_data

            frames_data.append(frame_data)
            frame_idx += 1
            processed_count += 1

            if processed_count % 50 == 0:
                fps_proc = processed_count / (time.time() - t0)
                print(f"[Pipeline] {processed_count} frames ({fps_proc:.1f} fps)")
                if progress_callback:
                    total = limit_frames if limit_frames else (total_frames // frame_stride)
                    progress_callback(min(1.0, processed_count / max(1, total)))

            if limit_frames and processed_count >= limit_frames:
                break

        cap.release()
        self.team_classifier.finalize()

        effective_fps = fps / frame_stride if fps > 0 else 0.0
        match_data = MatchTrackingData(
            match_id=match_id,
            video_filename=os.path.basename(video_path),
            fps=effective_fps,
            total_frames=processed_count,
            duration_seconds=processed_count / effective_fps if effective_fps > 0 else 0.0,
            frames=frames_data,
        )

        match_out_dir = Path(output_dir) / match_id
        match_out_dir.mkdir(parents=True, exist_ok=True)
        out_json_path = match_out_dir / "tracking.json"

        with open(out_json_path, "w") as f:
            f.write(json.dumps(match_data.model_dump(), indent=2))

        elapsed = time.time() - t0
        print(f"[Pipeline] Done: {processed_count} frames in {elapsed/60:.1f} min")
        print(f"[Pipeline] Output: {out_json_path}")
        return str(out_json_path)


if __name__ == "__main__":
    import argparse
    from backend.config import settings

    parser = argparse.ArgumentParser(description="MatchCast AI — Perception Pipeline")
    parser.add_argument("--video", required=True)
    parser.add_argument("--match-id", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--stride", type=int, default=15)
    parser.add_argument("--imgsz", type=int, default=416)
    parser.add_argument("--output-dir", default="data/outputs")
    args = parser.parse_args()

    src_points = PerceptionPipeline._parse_static_points(settings.STATIC_CAMERA_SRC_POINTS)
    pipeline = PerceptionPipeline(
        inference_size=args.imgsz,
        static_camera_mode=settings.STATIC_CAMERA_MODE,
        static_camera_src_points=src_points,
        jersey_ocr_enabled=settings.JERSEY_OCR_ENABLED,
        jersey_ocr_interval=settings.JERSEY_OCR_INTERVAL,
    )
    pipeline.process_video(
        args.video,
        args.match_id,
        output_dir=args.output_dir,
        limit_frames=args.limit,
        frame_stride=args.stride,
    )
