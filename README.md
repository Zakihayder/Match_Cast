# MatchCast AI

AI-powered football match analysis from video with:
- player/ball detection and tracking
- static-camera pitch mapping (full-field view)
- team assignment from jersey color
- optional jersey number OCR
- event extraction (shots, goals, assists, possession changes, dribbles, sprints, formation shifts)
- live scoreline and quality flags in the React dashboard

## Current Architecture

- Primary UI: React + Vite on localhost:5173
- API: FastAPI on localhost:8000
- CV pipeline: YOLOv8 + ByteTrack + custom analytics
- Optional Streamlit pages remain in app/ for legacy experimentation, but React is the main product surface.

## Repository Structure

- frontend/: React UI (upload, dashboard, replay, scoreline)
- backend/: FastAPI routes and app config
- perception/: detection, tracking, mapping, team classification, analytics
- scripts/: utility and validation scripts
- data/: local runtime data (ignored in git)
- generative/, intelligence/, storage/: next-phase integrations (scaffold)

## Prerequisites

- Python 3.10+
- Node.js 18+
- FFmpeg on PATH
- (Optional OCR) Tesseract OCR on PATH

## Setup

### 1) Python environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2) Frontend environment

```bash
cd frontend
npm install
copy .env.example .env
```

In frontend/.env:

```env
VITE_API_URL=http://127.0.0.1:8000
```

### 3) Backend environment

Copy root env:

```bash
cd ..
copy .env.example .env
```

Recommended CPU/static-camera settings in root .env:

```env
PROCESSING_FRAME_STRIDE=12
PROCESSING_FRAME_LIMIT=
STATIC_CAMERA_MODE=true
STATIC_CAMERA_SRC_POINTS=
JERSEY_OCR_ENABLED=false
JERSEY_OCR_INTERVAL=12
```

If you have accurate corner points (top-left, top-right, bottom-right, bottom-left):

```env
STATIC_CAMERA_SRC_POINTS=100,80;1820,80;1860,980;80,980
```

## Run

Use two terminals.

Terminal 1 (backend):

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 (frontend):

```bash
cd frontend
npm run dev
```

Open:
- http://localhost:5173

## Validation

### Tracking data sanity check

```bash
python scripts/verify_tracking.py data/outputs/<match_id>/tracking.json
```

### Goal/assist logic test without real video

```bash
python scripts/simulate_goal_assist_test.py
```

Expected: synthetic test passes with goal, assist, and score output.

## Notes on Accuracy

- Static full-field camera mode significantly improves identity consistency and team assignment.
- Jersey number OCR is best-effort and depends on image resolution, zoom, and player orientation.
- Analytics now emit:
  - score_a, score_b
  - quality_flags (duplicate/missed-goal and attribution warnings)

## License

MIT
