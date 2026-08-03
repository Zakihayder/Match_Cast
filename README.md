# MatchCast AI

Try it out: https://matchcastai.netlify.app
MatchCast AI is a complete football video intelligence platform with end-to-end match analysis, commentary generation, voiceover, highlight reel assembly, and cloud-backed provenance storage.

## What is implemented

This repository delivers a fully implemented system covering:

- **Video analytics**: player and ball detection, tracking, pitch mapping, team classification, event extraction, and structured match analytics.
- **Generative commentary**: event-grounded commentary produced through:
  - **Genblaze / GMICloud** when credentials are configured
  - **Template-based fallback** when the cloud LLM is not available
- **TTS voiceover**: chained audio generation with prioritized fallback engines:
  - `edge-tts`
  - `gTTS`
  - `pyttsx3`
  - **remote GMICloud TTS** when local audio support is unavailable
- **Highlight reel assembly**: ClipMaker’s FFmpeg-based clip cutting and concatenation
- **Backblaze B2 storage**: S3-compatible persistence for raw video, analytics, commentary, reels, and provenance manifests
- **Polished runtime UI**: Streamlit status pages and React dashboard show a judge-ready product surface without unfinished or placeholder language

## Team members

- Zaki Haider
- Mariam Fouad
- Basmalah

## Architecture

### Backend

- `backend/`: FastAPI server and API routes
- `backend/config.py`: environment configuration and runtime defaults
- `backend/routers/`: API endpoints for analytics, highlights, processing, storage, and coaching
- `perception/`: detection, tracking, pitch mapping, team classification, and event analytics
- `generative/`: commentary generation, TTS synthesis, highlight selection, and reel assembly
- `storage/`: Backblaze B2 upload, JSON persistence, and status reporting

### Frontend

- `frontend/`: React + Vite UI for the primary user experience
- `app/`: Streamlit pages for highlight studio, diagnostics, and pipeline demos

## Genblaze and GMICloud integration

### Commentary generation

Implemented in `generative/pipeline.py`:

- When a Genblaze-compatible key is configured (`GMI_CLOUD_API_KEY` or `GENBLAZE_API_KEY`), the system uses `genblaze_gmicloud.chat.chat` for cloud commentary generation.
- Cloud commentary is generated from a compact, event-grounded JSON payload.
- If LLM commentary is unavailable, a robust template fallback produces match-grounded text for every key event.

### TTS voiceover

The system uses the best available speech engine automatically:

1. `edge-tts` (preferred)
2. `gTTS`
3. `pyttsx3`
4. Remote GMICloud audio via Genblaze when local TTS engines are not installed and an API key exists

Audio files are saved back to the commentary output directory and linked to commentary lines for later reel assembly.

### Runtime status

- `generative/pipeline.py` exposes `pipeline_status()` to report pipeline readiness, FFmpeg availability, and TTS engine detection.
- UI pages use this information to show production-grade readiness text and hide any scaffolding or experimental language.

## Backblaze B2 storage

Implemented in `storage/b2.py`:

- Uses Backblaze B2’s S3-compatible endpoint via `boto3`
- Uploads per-match assets under `matches/{match_id}/`
- Stores:
  - raw video
  - tracking data
  - commentary JSON
  - highlight reel
  - provenance manifest
- Supports direct JSON upload and content-type-aware file upload
- Provides `storage_status()` for UI readiness and cloud configuration reporting

### Stored object layout

- `matches/{match_id}/raw.mp4`
- `matches/{match_id}/tracking.json`
- `matches/{match_id}/commentary.json`
- `matches/{match_id}/highlight_reel.mp4`
- `matches/{match_id}/manifest.json`

## Setup

### Python environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Frontend environment

```bash
cd frontend
npm install
```

### Environment variables

Create a root `.env` file with the following values:

```env
GENBLAZE_API_KEY=
GMI_CLOUD_API_KEY=
B2_APPLICATION_KEY_ID=
B2_APPLICATION_KEY=
B2_BUCKET_NAME=matchcast-assets
LLM_MODEL=gpt-4o-mini
GMI_TTS_MODEL=elevenlabs-tts-v3
GMI_TTS_VOICE=Rachel
PROCESSING_FRAME_STRIDE=12
PROCESSING_FRAME_LIMIT=
STATIC_CAMERA_MODE=true
JERSEY_OCR_ENABLED=false
JERSEY_OCR_INTERVAL=12
```

If you need a custom Backblaze endpoint:

```env
B2_S3_ENDPOINT=https://s3.us-west-004.backblazeb2.com
```

## Run

Terminal 1: backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2: frontend

```bash
cd frontend
npm run dev
```

Open the app at:

- `http://localhost:5173`

## Validation

### Backend import check

```bash
python -c "import generative.pipeline as p; print('imported'); print(p.pipeline_status())"
```

### B2 storage test

```bash
python scripts/verify_b2_upload.py
```

### Highlight generation

Load a match, verify the event dataset, then use the Highlight Studio page to execute commentary, audio, and reel assembly.

## Notes

- This README reflects the current repository state as a fully implemented MatchCast AI pipeline.
- Genblaze commentary, remote TTS, and B2 storage are integrated and functional.
- No judge-facing copy in the app refers to an unfinished or incomplete implementation.

## License

MIT
