# Antigravity Build Prompt — MatchCast AI

Paste this whole thing into Antigravity as your project brief. It's written to minimize the two failure modes that kill hackathon builds: scope creep and silent, undetected mistakes in early phases that break everything downstream.

---

## Project

Build **MatchCast AI**: a pipeline that takes a football/soccer match video clip and produces (1) tracked player positions in real pitch coordinates, (2) detected events and formation shifts, (3) a top-down radar replay + clickable timeline, (4) an AI-generated highlight reel with commentary, voiceover, and tactical graphics via **Genblaze**, and (5) an AI Coach that gives data-grounded tactical feedback.

I am the sole engineer on the core pipeline. Build in strict phase order below — do not start a phase until the previous phase's exit criteria are met. Do not silently substitute libraries, skip validation steps, or "improve" the architecture without flagging it to me first.

## This is for the Backblaze Generative AI Media Hackathon — build to these scoring criteria

Judging is Stage One (pass/fail — does the project reasonably fit the theme and use B2 + Genblaze at all) then Stage Two, scored equally across four criteria. Every phase below should visibly serve at least one of these:

1. **Real-world utility** — solves a real problem for a real audience (coaches/players reviewing match footage), not just a tech demo.
2. **Production readiness** — functions reliably beyond a one-off demo run: error handling, fallbacks, repeatable on a new clip.
3. **B2 storage + data orchestration** — B2 must be used *meaningfully*: storing generated media, metadata, provenance records, thumbnails, logs, not just a single video dump.
4. **Use of Genblaze** — must *meaningfully orchestrate* generative workflows across steps/providers, not just fire one isolated API call. Chaining commentary → TTS → graphics as an actual Genblaze pipeline (not three disconnected calls) is what this criterion rewards.

**Required at submission** (build toward these from day one, don't bolt them on at the end):
- A working, publicly accessible app URL judges can test without needing us present
- A public (or private-with-`b2genblaze`-access) GitHub repo with real setup instructions in the README
- An explicit list of every AI provider/model used (e.g. "GMI Cloud: [model name] for commentary, ElevenLabs via Genblaze for TTS")
- A written explanation of how the app uses B2 and Genblaze specifically
- A ≤3-minute demo video — judges are not required to watch past 3 minutes, so the highlight-reel-generation-and-payoff needs to land early, not at the end

Keep this in mind as a running checklist — flag to me if any phase risks leaving one of these criteria thin.

## Non-negotiable ground rules

1. **Validate visually before trusting metrics, every single time a detection/tracking/calibration step is added.** If you write code that produces bounding boxes, tracked IDs, or pitch coordinates, also produce a way for me to *see* the output overlaid on a frame or pitch diagram before moving on. Never assume correctness from clean-looking numbers alone.
2. **Lock the output schema in Phase 1 and do not change it later without telling me explicitly.** Every phase after Phase 1 reads from this schema. A silent field rename or type change downstream is the single most likely way this project breaks.
3. **Homography/calibration (Phase 1, Step 3) is the highest-risk step in the whole project.** Do not rush it. Show me the transformed points plotted on a top-down pitch diagram and get my confirmation that positions look sane before proceeding to Phase 2.
4. **Every generative call (Genblaze commentary, TTS, graphics) must be fed concrete data — real timestamps, real player IDs, real positions/scores — never vague summaries.** If you can't ground a prompt in real numbers from the tracking dataset, tell me instead of generating something generic.
5. **Build fallbacks for anything that calls an external API** (Genblaze, B2). If TTS fails or times out, the pipeline must still surface text commentary rather than crashing the whole highlight reel. Tell me explicitly everywhere you've added a fallback so I know where the weak points are.
5a. **Use Genblaze's Pipeline/Step abstraction to chain commentary → TTS → graphics, not three standalone provider calls.** This is directly what the "Use of Genblaze" judging criterion rewards, and it also gives us provenance manifests for free — store those manifests in B2 alongside the assets they describe, since that's what the "B2 storage + data orchestration" criterion is looking for (metadata/provenance, not just raw files).
6. **Frontend: use Streamlit, not React.** This is deliberate, not a placeholder — do not suggest migrating to React/a separate backend API unless I ask. Time is the scarce resource here; polish Streamlit with custom CSS and a clean SVG/Canvas radar component instead of rebuilding infrastructure.
7. **When you're unsure whether something is in scope, ask me — don't guess and build it anyway.** Especially for Phase 5 (stretch features): only touch these if I explicitly confirm we're ahead of schedule.
8. **After finishing each phase, stop and summarize**: what you built, what you validated, what's still shaky, and what exit criteria are or aren't met. Wait for my go-ahead before starting the next phase.

## Environment

- Python 3.10+, virtual environment
- Core libs: `ultralytics` (YOLOv8), `supervision` (ByteTrack wrapper), `opencv-python`, `numpy`, `streamlit`
- Genblaze SDK: `pip install genblaze-core genblaze-s3` plus provider adapters — start with `genblaze-gmicloud` (GMI Cloud gives hackathon participants free credits and covers text/image/audio/chat behind one key) and add `genblaze-elevenlabs` or another TTS adapter only if GMI Cloud's audio quality isn't good enough for commentary voiceover. I will provide the actual API keys once accounts are created.
- Backblaze B2 account + application key + a bucket for this project (I will provide credentials). Use Genblaze's `S3StorageBackend.for_backblaze("bucket-name")` instead of hand-rolling a `boto3` wrapper — it's built for this exact use case and gives us provenance-aware, content-addressable storage for free.
- Reference repos to look at before writing pipeline code: `backblaze-labs/genblaze` (main SDK), and the two official sample pipelines `genblaze-gen-media-multi-provider-sample` and `genblaze-gmicloud-pipeline`.
- Repo structure:
```
/perception     → detection, tracking, calibration
/intelligence   → coach logic, match chat, summaries
/generative     → genblaze orchestration
/storage        → b2 client wrapper
/app            → streamlit frontend
/data           → sample clips, test outputs (gitignored if large)
```

## Phase 1 — Perception Foundation

**Goal:** turn a video into a structured dataset of player positions in real pitch coordinates.

1. Start from a pretrained YOLOv8 model, fine-tune on a football dataset (SoccerNet or a Roboflow football player-detection set). Run inference on a few sample frames first and show me the boxes before trusting any metrics.
2. Use `supervision`'s ByteTrack wrapper to assign persistent player IDs across frames. Test on a full clip, not single frames — watch for and report ID switches.
3. Homography/pitch calibration: manually mark 4+ known reference points (corner flags, penalty box corners, center circle) in one frame, compute the homography matrix with `cv2.findHomography()`, map to a real pitch coordinate system (105m x 68m, meters or normalized 0-1). Apply to every detected position. **Show me the overlay on a top-down pitch diagram before proceeding.**
4. Lock this output schema exactly:
```json
{
  "frame": 1234,
  "timestamp": 51.4,
  "players": [
    {"id": 7, "team": "A", "pitch_x": 34.2, "pitch_y": 12.8}
  ],
  "ball": {"pitch_x": 40.1, "pitch_y": 30.5}
}
```
Store per match as JSON/Parquet.

**Exit criteria:** full test clip produces clean, sensible pitch-coordinate data for every frame with stable player IDs. Confirm with me before Phase 2.

## Phase 2 — Events, Formations, Radar Replay, Timeline

1. Formation-change detection: cluster each team's players into lines (defense/midfield/attack) by pitch_y at each timestamp. Track cluster shape over a rolling ~30s window; flag a shift when line structure changes significantly. Keep thresholds configurable — we'll tune by eye.
2. Event detection (heuristic, not ML): sprints (large frame-to-frame deltas), possession changes (ball-to-player proximity crossing a threshold over consecutive frames), shots/dangerous attacks (ball moving rapidly toward a goal-area zone). Log timestamp, type, involved player IDs for each.
3. Radar-view replay: top-down pitch (SVG/Canvas via Streamlit HTML component), animate player dots from pitch-coordinate data. This is the safety-net demo — prioritize it looking clean and running smoothly independent of everything downstream.
4. Smart Match Timeline: clickable list of detected events that jumps the video player and/or radar replay to that timestamp.

**Exit criteria:** formation detection gives sensible results, radar replay is smooth, timeline correctly jumps to moments. Confirm with me before Phase 3.

## Phase 3 — Generative Pipeline via Genblaze

Build this as one chained Genblaze `Pipeline` (text step → audio step → image step), not three separate isolated API calls — this is what the hackathon's "Use of Genblaze" scoring criterion is actually looking for, and it gets us a provenance manifest for free at the end.

1. Commentary: for each detected event/formation shift, build a structured prompt with concrete data (event type, timestamp, players, score context) as the text step in the pipeline. Ground every prompt in real numbers.
2. TTS: chain commentary text into an audio step, synced to the clip's timestamp. Build the fallback (text-only) explicitly and tell me it's there.
3. Tactical graphics: for each formation-change event, chain an image-generation step producing a before/after shape graphic, or fall back to a programmatically rendered diagram if generation fails.
4. Highlight assembly: stitch trimmed clips + commentary audio + graphics into one video via `moviepy` or `ffmpeg` (this part is standard video editing, not a Genblaze step).
5. B2 storage: use `S3StorageBackend.for_backblaze("bucket-name")` to store per match, under a consistent key structure: raw video, tracking JSON, the Genblaze provenance manifest, commentary text, audio, graphics, and the final reel — e.g. `matches/{match_id}/raw.mp4`, `matches/{match_id}/manifest.json`, `matches/{match_id}/reel.mp4`. Storing the manifest is not optional — it's direct evidence for the B2 + Genblaze judging criteria.
6. Keep a running list of every provider/model actually used (e.g. "GMI Cloud — [model] for text, [model] for TTS") — I need this verbatim for the submission's required provider/model list.

**Exit criteria:** one full highlight reel generated end-to-end via a single chained pipeline, with all assets *and* the provenance manifest stored and retrievable from B2. Confirm with me before Phase 4.

## Phase 4 — Intelligence Layer

1. AI Coach: prompt an LLM with aggregated match stats (formation changes, event counts, per-half comparisons). **Require it to cite the specific data point behind every recommendation** — enforce this as a system prompt constraint. Reject/regenerate output that makes claims without a traceable stat behind them.
2. Player performance summaries (only if ahead of schedule): distance covered, sprint count, event involvement, LLM write-up explicitly framed as a performance summary, not a talent evaluation.

**Exit criteria:** every AI Coach claim is traceable to a real stat, not generic filler.

## Phase 5 — Stretch (only if explicitly told we're ahead of schedule)

Priority order — stop wherever time runs out:
1. Heatmaps (reuses Phase 1 data)
2. Momentum graph (event density + territorial position over time)
3. Highlight intro polish
4. AI Match Chat — scope strictly to filterable/aggregation queries over the structured dataset via a small set of callable functions the LLM selects from, not open-ended reasoning
5. Multilingual commentary, personalized per-player highlights

## Tech stack summary

| Layer | Tools |
|---|---|
| Detection | YOLOv8 (Ultralytics) |
| Tracking | ByteTrack via `supervision` |
| Calibration | OpenCV homography |
| Frontend | Streamlit (polished with custom CSS + SVG/Canvas radar) |
| Generative | Genblaze SDK (Pipeline/Step chaining text → audio → image, provider: GMI Cloud primary) |
| Video assembly | `moviepy` / `ffmpeg` |
| Storage | Backblaze B2 via Genblaze's `S3StorageBackend.for_backblaze()` |

## Before final submission

- Confirm the GitHub repo has a real README with setup instructions — this is a required submission field, not optional documentation.
- If the repo is private, grant contributor access to `https://github.com/b2genblaze`.
- Draft the "how this app uses B2 and Genblaze" explanation from what was actually built, not aspirationally — cross-check every claim against the running provider/model list from Phase 3.
- Deploy the app somewhere judges can access without us present, and test that link cold before submitting.
- Demo video must be ≤3 minutes — put the highlight-reel payoff early, since judges aren't required to watch past the 3-minute mark.

---

Start with Phase 0 (environment setup) and Phase 1, Step 1.1 only. Stop and report back before continuing.
