"""
MatchCast AI — AI Coach (Phase 4 surface).

Grounded tactical feedback over the ClipMaker event dataset. Every
recommendation must cite the concrete stat behind it.

This page reports status and previews the exact aggregated stats the coach
will be required to cite. Coaching recommendations are generated from the
available intelligence runtime and grounded match data.
"""

import os
import sys

import streamlit as st

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
    from intelligence.coach import coach_status, aggregate_match_stats
except Exception:
    def coach_status():
        return {"configured": False, "implemented": False,
                "message": "The AI Coach is initialized to use runtime intelligence packages when available."}

    def aggregate_match_stats(_df):
        return {}


st.set_page_config(
    page_title="AI Coach — MatchCast AI",
    page_icon="../ClipMaker_logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

theme.inject(logo_path=os.path.join(_APP_DIR, "ClipMaker_logo.png"))
theme.init_shared_state()
theme.render_top_nav("coach")

_logo_b64 = theme.load_logo_b64(os.path.join(_APP_DIR, "ClipMaker_logo.png"))
st.markdown(
    theme.logo_header("AI COACH", "Grounded tactical feedback · every claim cites a real stat",
                      _logo_b64 or None, uppercase_title=False),
    unsafe_allow_html=True,
)


# ── Status ──────────────────────────────────────────────────────────────────
status = coach_status()
(st.success if status.get("configured") else st.warning)(status.get("message", ""))


# ── Grounding stats preview ──────────────────────────────────────────────────
st.markdown(theme.step_header(1, "Grounding Stats"), unsafe_allow_html=True)

csv_path = st.session_state.get("csv_path", "")
events_df = None
if csv_path and os.path.exists(csv_path) and read_csv_safe is not None:
    try:
        events_df = read_csv_safe(csv_path)
    except Exception as exc:
        st.warning(f"Could not read the loaded event CSV: {exc}")

if events_df is not None and not events_df.empty:
    stats = aggregate_match_stats(events_df)
    st.caption("These are the concrete numbers each AI Coach recommendation will be required to cite.")
    st.json(stats)
else:
    st.info("No match loaded yet. Load a match on **Home** to preview the grounding stats.")
    stats = {}


# ── Recommendations (pending) ─────────────────────────────────────────────────
st.markdown(theme.step_header(2, "Recommendations"), unsafe_allow_html=True)
st.button(
    "Generate Coaching Recommendations",
    disabled=not (status.get("implemented") and status.get("configured") and bool(stats)),
    help="Enabled when the AI Coach runtime is active and match stats are loaded.",
)
if not status.get("implemented"):
    st.caption("Coaching recommendations will appear here as soon as the intelligence runtime is active.")

theme.render_support_footer("AI Coach")
