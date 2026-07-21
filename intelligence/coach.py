"""
MatchCast AI — AI Coach (Phase 4, scaffold).

Intended design: prompt an LLM with the match's aggregated event-data stats
(possession, xT, progressive actions, box entries, per-half comparisons, etc.
derived from the ClipMaker event dataset) and REQUIRE every recommendation to
cite the concrete stat behind it. Output that makes a claim with no traceable
stat is rejected/regenerated.

This module is currently a scaffold: the aggregation helper is real (it works
off the ClipMaker events DataFrame), but the LLM call is not implemented yet.
"""

from typing import Any

try:
    from matchcast_settings import genblaze_configured
except Exception:  # pragma: no cover
    def genblaze_configured() -> bool:
        return False


def coach_status() -> dict:
    """Report whether the AI Coach can run."""
    configured = genblaze_configured()
    return {
        "configured": configured,
        "implemented": False,
        "message": (
            "LLM credentials detected — AI Coach implementation pending."
            if configured
            else "No LLM provider key found in .env. Add GMI_CLOUD_API_KEY or "
            "GENBLAZE_API_KEY to enable grounded AI Coach recommendations."
        ),
    }


def aggregate_match_stats(events_df) -> dict[str, Any]:
    """
    Build a compact, LLM-ready stats summary from a ClipMaker events DataFrame.

    Kept dependency-light and defensive so it works with partial data. These are
    exactly the numbers each AI Coach recommendation must cite.
    """
    stats: dict[str, Any] = {}
    if events_df is None or getattr(events_df, "empty", True):
        return stats

    try:
        df = events_df
        stats["total_events"] = int(len(df))
        if "team" in df.columns:
            stats["events_by_team"] = {
                str(k): int(v) for k, v in df["team"].value_counts().items()
            }
        if "type" in df.columns:
            stats["events_by_type"] = {
                str(k): int(v) for k, v in df["type"].value_counts().head(15).items()
            }
        if "xT" in df.columns:
            xt = df["xT"].dropna()
            if len(xt) > 0 and "team" in df.columns:
                stats["xT_by_team"] = {
                    str(k): round(float(v), 3)
                    for k, v in df.groupby("team")["xT"].sum().items()
                }
        if "period" in df.columns:
            stats["events_by_period"] = {
                str(k): int(v) for k, v in df["period"].value_counts().items()
            }
    except Exception:
        # Never let stat aggregation crash the page.
        pass
    return stats


class AICoach:
    """Grounded tactical-recommendation generator (scaffold)."""

    def __init__(self) -> None:
        self.status = coach_status()

    def recommend(self, events_df) -> list[dict]:
        """Return grounded recommendations, each citing a stat. Not implemented yet."""
        raise NotImplementedError(
            "AI Coach LLM call is not implemented yet. It will consume "
            "aggregate_match_stats(events_df) and require a cited stat per claim."
        )
