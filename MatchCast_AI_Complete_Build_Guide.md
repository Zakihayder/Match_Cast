# MatchCast AI — Complete Technical Build Guide
**For the technical lead building Tiers 1–2 solo, with generative/integration work in Phases 3–4**

This guide assumes you are the sole engineer on the core pipeline, with two teammates handling documentation, testing, design, and presentation (see work-division note). It walks through each phase in build order, with concrete steps, not just architecture.

---

## 0. Environment Setup (Day 1, before Phase 1 starts)

- Python 3.10+, virtual environment.
- Core libraries: `ultralytics` (YOLOv8), `bytetrack` (or `supervision` library, which wraps ByteTrack cleanly), `opencv-python`, `numpy`, `streamlit`.
- Genblaze API access + keys.
- Backblaze B2 account, application key, and a bucket created (`matchcast-assets` or similar).
- Get 2–3 sample match video clips early (Teammate 2's job to source, but you need at least one placeholder immediately to start testing against).
- Set up a shared repo (GitHub) with a clear folder structure from day one:
```
/perception      → detection, tracking, calibration
/intelligence    → coach logic, match chat, summaries
/generative      → genblaze orchestration
/storage         → b2 client wrapper
/app             → streamlit frontend
/data            → sample clips, test outputs (gitignored if large)
```

---

## Phase 1 — Perception Foundation (Days 1–7)

**Goal:** turn a video into a structured dataset of player positions in real pitch coordinates.

### Step 1.1 — Player & ball detection
- Start from a pretrained YOLOv8 model, fine-tune on a football/soccer dataset (SoccerNet, or a Roboflow football player-detection set).
- Fine-tuning workflow: export dataset in YOLO format → `yolo train model=yolov8n.pt data=data.yaml epochs=50-100`.
- Validate visually first — run inference on a few frames of your sample clip and eyeball the boxes before trusting metrics.

### Step 1.2 — Tracking
- Use `supervision`'s ByteTrack wrapper (much less boilerplate than raw ByteTrack) to assign persistent IDs to each detected player across frames.
- Test on a full clip, not just single frames — ID switches (a player's ID changing mid-clip) are the main failure mode to watch for.

### Step 1.3 — Homography / pitch calibration
- For your fixed/semi-fixed camera clip: manually mark 4+ known reference points (corner flags, penalty box corners, center circle) in one frame.
- Compute the homography matrix with `cv2.findHomography()` using those points mapped to real-world pitch coordinates (a standard pitch is 105m x 68m — define your coordinate system in meters or normalized 0–1).
- Apply this matrix to every detected player position in every frame to get pitch coordinates instead of pixel coordinates.
- **This is your highest-risk step.** Budget extra time here. Test by overlaying the transformed points on a top-down pitch diagram and visually confirming players land in sensible positions.

### Step 1.4 — Output schema
Define and lock this early — everything downstream depends on it:
```json
{
  "frame": 1234,
  "timestamp": 51.4,
  "players": [
    {"id": 7, "team": "A", "pitch_x": 34.2, "pitch_y": 12.8},
    ...
  ],
  "ball": {"pitch_x": 40.1, "pitch_y": 30.5}
}
```
Store this as a structured file (JSON/Parquet) per match — this is what Phases 2–4 all read from.

**Phase 1 exit criteria:** running your pipeline on a full test clip produces clean, sensible pitch-coordinate data for every frame, with stable player IDs.

---

## Phase 2 — Events, Formations, Radar Replay, Timeline (Days 7–11)

### Step 2.1 — Formation-change detection (heuristic)
- Cluster each team's players into lines (defense/midfield/attack) by their pitch_y coordinate at each timestamp.
- Track the shape of these clusters over a rolling window (e.g. every 30 seconds); flag a "formation shift" when the line structure changes significantly (e.g. defensive line width changes by more than a threshold, or the number of distinct lines changes).
- Keep the threshold values configurable — you'll tune these by eye against your sample clip.

### Step 2.2 — Event detection (heuristic)
- Sprints: large frame-to-frame position deltas for a player.
- Possession changes: proximity of the ball to a player crossing a distance threshold, tracked over consecutive frames.
- Shots/dangerous attacks: ball moving rapidly toward a goal-area zone.
- Log each detected event with a timestamp, type, and involved player IDs — this feeds both the timeline and later the AI Coach/commentary.

### Step 2.3 — Radar-view replay
- Render a simple top-down pitch (SVG or Canvas via Streamlit/HTML component) and animate player dots using your pitch-coordinate data, frame by frame or at a reduced sample rate for performance.
- This is your safety-net demo — make sure it looks clean and runs smoothly even if nothing downstream is finished yet.

### Step 2.4 — Smart Match Timeline
- Simple UI list of detected events (from 2.2), each clickable, jumping the video player and/or radar replay to that timestamp.

**Phase 2 exit criteria:** formation-change detection produces sensible results on your test clip, radar replay is smooth and clear, and the timeline correctly jumps to moments in the video.

---

## Phase 3 — Generative Pipeline via Genblaze (Days 11–15)

### Step 3.1 — Commentary generation
- For each detected event (Phase 2.2) and formation shift (Phase 2.1), construct a structured prompt with the concrete data (event type, timestamp, players involved, score context) and call Genblaze's text generation to produce a short commentary line.
- Keep prompts data-grounded — feed in actual numbers/positions, not vague descriptions, so output reads as specific rather than generic.

### Step 3.2 — Voiceover / TTS
- Pass generated commentary text to Genblaze's voice/TTS capability, synced to the relevant clip's timestamp.
- Build a fallback: if TTS fails or times out, the pipeline should still surface the text commentary rather than breaking the whole reel.

### Step 3.3 — Tactical graphics
- For each formation-change event, generate a simple graphic (via Genblaze image generation or a programmatically rendered diagram) showing the before/after shape.

### Step 3.4 — Highlight assembly
- Stitch selected clips (trimmed around key events) + commentary audio + graphic overlays into one video file, using `moviepy` or `ffmpeg` directly for assembly (Genblaze handles the generative pieces; assembly itself is standard video editing code).

### Step 3.5 — B2 storage wiring
- Wrap the B2 API (S3-compatible, so `boto3` works with B2's endpoint) in a small storage client.
- Store per match: raw video, tracking dataset JSON, generated commentary text, audio files, graphics, final assembled reel — under a consistent key structure, e.g. `matches/{match_id}/raw.mp4`, `matches/{match_id}/tracking.json`, `matches/{match_id}/reel.mp4`.

**Phase 3 exit criteria:** one full highlight reel generated end-to-end from a test clip, with all assets stored and retrievable from B2.

---

## Phase 4 — Intelligence Layer (Days 15–17)

### Step 4.1 — AI Coach
- Prompt an LLM with the match's aggregated stats (formation changes, event counts, per-half comparisons) and require it to **cite the specific data point behind each recommendation** in its output (e.g. "Your defensive line dropped 8 meters deeper after minute 60, coinciding with 3 shots conceded — consider holding the line higher in the final third").
- This citation requirement is a prompt-design constraint, not new infrastructure — enforce it directly in the system prompt.

### Step 4.2 — Player performance summaries (if time allows)
- Per player: distance covered (sum of frame-to-frame position deltas), sprint count, involvement in logged events.
- LLM-generated short qualitative write-up from these stats — explicitly framed as a performance summary, not a talent evaluation.

**Phase 4 exit criteria:** AI Coach output reads as genuinely grounded (every claim traceable to a real stat), not generic filler.

---

## Phase 5 — Stretch Features (Days 17–18, only if ahead of schedule)

In priority order, stop at whichever point Day 18 arrives:
1. Heatmaps (density plot of a player's pitch positions — cheap, reuses Phase 1 data).
2. Momentum graph (simple rolling score combining event density + territorial position over time).
3. Highlight video intro polish (auto-generated match summary card at the start of the reel).
4. AI Match Chat — scope strictly to filterable/aggregation queries over your structured dataset (e.g. "show every attack from the left side" = filter events by zone; "compare first and second half" = aggregate stats by time window). Implement as a small set of callable functions the LLM selects from, not open-ended reasoning.
5. Multilingual commentary, personalized per-player highlights.

---

## Final Days — Integration & Submission

- Full end-to-end run on your best sample clip — this becomes your demo video source.
- Confirm every claim in your Devpost write-up matches what the app actually does (this is where Teammate 2's QA role matters most).
- Record the demo video (Teammate 3), covering: upload → radar replay → timeline → highlight reel → AI Coach output, in that order, since it mirrors your architecture and is easy for judges to follow.
- Submit with buffer days (Aug 2–3) held in reserve for last-minute fixes.

---

## Quick Reference — Tech Stack Summary

| Layer | Tools |
|---|---|
| Detection | YOLOv8 (Ultralytics) |
| Tracking | ByteTrack via `supervision` |
| Calibration | OpenCV homography |
| Frontend | Streamlit |
| Generative | Genblaze (text, voice, image) |
| Video assembly | `moviepy` / `ffmpeg` |
| Storage | Backblaze B2 (via `boto3`, S3-compatible) |
