"""
MatchCast AI — Highlight Studio (Phase 3 surface).

Where the ClipMaker event spine meets the Genblaze generative pipeline:
commentary -> voiceover -> tactical graphics -> highlight reel, with assets +
provenance stored in Backblaze B2.

This page is the scaffold surface: it reports integration status, previews the
loaded match/event data the pipeline will consume, and lays out the pipeline
steps. Generation is enabled once the generative/storage layers are implemented
and credentials are present.
"""

import os
import sys

import streamlit as st

# app/ dir on path (for theme + clipmaker_core), then repo root (for the
# generative/intelligence/storage packages + shared settings).
_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _APP_DIR)
_REPO_ROOT = os.path.dirname(_APP_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import theme

try:
    from clipmaker_core import read_csv_safe
except Exception:
    read_csv_safe = None

try:
    from generative.pipeline import pipeline_status
except Exception:
    def pipeline_status():
        return {"configured": False, "implemented": False,
                "message": "generative package not importable."}

try:
    from storage.b2 import storage_status
except Exception:
    def storage_status():
        return {"configured": False, "implemented": False, "bucket": "matchcast-assets",
                "message": "storage package not importable."}


st.set_page_config(
    page_title="Highlight Studio — MatchCast AI",
    page_icon="../ClipMaker_logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

theme.inject(logo_path=os.path.join(_APP_DIR, "ClipMaker_logo.png"))
theme.init_shared_state()
theme.render_top_nav("studio")

_logo_b64 = theme.load_logo_b64(os.path.join(_APP_DIR, "ClipMaker_logo.png"))
st.markdown(
    theme.logo_header("HIGHLIGHT STUDIO", "Genblaze pipeline · commentary → voiceover → graphics → reel",
                      _logo_b64 or None, uppercase_title=False),
    unsafe_allow_html=True,
)


# ── Loaded match / event data preview ──────────────────────────────────────
st.markdown(theme.step_header(1, "Match Data"), unsafe_allow_html=True)

csv_path = st.session_state.get("csv_path", "")
events_df = None
if csv_path and os.path.exists(csv_path) and read_csv_safe is not None:
    try:
        events_df = read_csv_safe(csv_path)
    except Exception as exc:
        st.warning(f"Could not read the loaded event CSV: {exc}")

if events_df is not None and not events_df.empty:
    home = str(events_df["homeTeam"].dropna().iloc[0]) if "homeTeam" in events_df.columns and not events_df["homeTeam"].dropna().empty else "?"
    away = str(events_df["awayTeam"].dropna().iloc[0]) if "awayTeam" in events_df.columns and not events_df["awayTeam"].dropna().empty else "?"
    c1, c2, c3 = st.columns(3)
    c1.metric("Match", f"{home} vs {away}")
    c2.metric("Events", f"{len(events_df):,}")
    goals = int((events_df["type"] == "Goal").sum()) if "type" in events_df.columns else 0
    c3.metric("Goals", goals)
else:
    st.info("No match loaded yet. Go to **Home** to scrape or load a match, then set kick-off timestamps on **Filtering/Output**.")


# ── Integration status ──────────────────────────────────────────────────────
st.markdown(theme.step_header(2, "Generative Pipeline Status"), unsafe_allow_html=True)

gen = pipeline_status()
b2 = storage_status()

gcol, bcol = st.columns(2)
with gcol:
    st.markdown("**Genblaze (GMI Cloud)**")
    (st.success if gen.get("configured") else st.warning)(gen.get("message", ""))
with bcol:
    st.markdown("**Backblaze B2**")
    (st.success if b2.get("configured") else st.warning)(b2.get("message", ""))

st.markdown(theme.step_header(3, "Pipeline Plan"), unsafe_allow_html=True)
st.markdown(
    """
1. **Commentary (text)** — one data-grounded line per key event (real timestamps, players, xT).
2. **Voiceover (TTS)** — chained from the commentary text, with a text-only fallback.
3. **Tactical graphics (image)** — before/after shape for formation shifts.
4. **Reel assembly** — ClipMaker's FFmpeg cutter stitches clips + audio + graphics.
5. **B2 storage** — raw video, event data, provenance manifest, and final reel.
    """
)

st.button(
    "Generate Highlight Reel",
    disabled=not (gen.get("implemented") and gen.get("configured")),
    help="Enabled once the Genblaze pipeline is implemented and credentials are set.",
)
if not gen.get("implemented"):
    st.caption("Generation is not wired up yet — this is the Phase 3 build surface.")

theme.render_support_footer("Highlight Studio")
