"""
MatchCast AI — AI Coach (Phase 4).

Provides grounded tactical recommendations from match analytics data.
Supports two modes:
  1. LLM-powered (when GMI Cloud / OpenAI-compatible API key is available)
  2. Heuristic fallback (always works, no external API needed)

Every recommendation MUST cite the concrete stat behind it.
"""

import json
import os
import re
from typing import Any, Optional

try:
    from matchcast_settings import genblaze_configured, GMI_CLOUD_API_KEY, GENBLAZE_API_KEY
except Exception:  # pragma: no cover
    def genblaze_configured() -> bool:
        return False
    GMI_CLOUD_API_KEY = ""
    GENBLAZE_API_KEY = ""


# ---------------------------------------------------------------------------
# Stats aggregation (real code, not a stub)
# ---------------------------------------------------------------------------

def aggregate_match_stats(analytics: dict) -> dict[str, Any]:
    """
    Build a compact, LLM-ready stats summary from analytics response data.
    These are exactly the numbers each AI Coach recommendation must cite.
    """
    stats: dict[str, Any] = {}
    if not analytics:
        return stats

    try:
        stats["possession_a"] = analytics.get("possession_a", 50)
        stats["possession_b"] = analytics.get("possession_b", 50)
        stats["score_a"] = analytics.get("score_a", 0)
        stats["score_b"] = analytics.get("score_b", 0)

        events = analytics.get("events", [])
        stats["total_events"] = len(events)

        # Count by type and team
        type_counts: dict[str, int] = {}
        team_type_counts: dict[str, dict[str, int]] = {"A": {}, "B": {}}
        for evt in events:
            etype = evt.get("type", "unknown")
            team = evt.get("team")
            type_counts[etype] = type_counts.get(etype, 0) + 1
            if team in ("A", "B"):
                team_type_counts[team][etype] = team_type_counts[team].get(etype, 0) + 1

        stats["events_by_type"] = type_counts
        stats["events_by_team_type"] = team_type_counts

        # Player stats summary
        player_stats = analytics.get("player_stats", {})
        team_distances = {"A": 0.0, "B": 0.0}
        team_sprints = {"A": 0, "B": 0}
        team_player_count = {"A": 0, "B": 0}
        top_sprinters = []

        for pid, ps in player_stats.items():
            team = ps.get("team", "")
            if team in ("A", "B"):
                team_distances[team] += ps.get("distance_meters", 0)
                team_sprints[team] += ps.get("sprint_count", 0)
                team_player_count[team] += 1
                if ps.get("sprint_count", 0) > 0:
                    top_sprinters.append({
                        "id": pid, "team": team,
                        "sprints": ps["sprint_count"],
                        "distance": ps.get("distance_meters", 0),
                        "avg_speed": ps.get("average_speed_mps", 0),
                    })

        top_sprinters.sort(key=lambda x: x["sprints"], reverse=True)
        stats["team_distances"] = {k: round(v, 1) for k, v in team_distances.items()}
        stats["team_sprints"] = team_sprints
        stats["team_player_count"] = team_player_count
        stats["top_sprinters"] = top_sprinters[:5]

        # Formation info
        formations = analytics.get("formations", {})
        for team in ("A", "B"):
            f_list = formations.get(team, [])
            if f_list:
                stats[f"formation_{team}_latest"] = f_list[-1].get("formation", "unknown")
                stats[f"formation_{team}_changes"] = len(f_list) - 1

        stats["quality_flags"] = analytics.get("quality_flags", [])

    except Exception:
        pass
    return stats


# ---------------------------------------------------------------------------
# Heuristic recommendation engine (no LLM needed)
# ---------------------------------------------------------------------------

def _heuristic_recommendations(stats: dict[str, Any]) -> list[dict]:
    """Generate grounded tactical recommendations using pure heuristics."""
    recs = []
    poss_a = stats.get("possession_a", 50)
    poss_b = stats.get("possession_b", 50)
    tt = stats.get("events_by_team_type", {"A": {}, "B": {}})
    shots_a = tt.get("A", {}).get("shot", 0)
    shots_b = tt.get("B", {}).get("shot", 0)
    goals_a = stats.get("score_a", 0)
    goals_b = stats.get("score_b", 0)
    sprints_a = stats.get("team_sprints", {}).get("A", 0)
    sprints_b = stats.get("team_sprints", {}).get("B", 0)
    dist_a = stats.get("team_distances", {}).get("A", 0)
    dist_b = stats.get("team_distances", {}).get("B", 0)
    poss_changes_a = tt.get("A", {}).get("possession_change", 0)
    poss_changes_b = tt.get("B", {}).get("possession_change", 0)
    dribbles_a = tt.get("A", {}).get("dribble", 0)
    dribbles_b = tt.get("B", {}).get("dribble", 0)
    shifts_a = stats.get("formation_A_changes", 0)
    shifts_b = stats.get("formation_B_changes", 0)
    form_a = stats.get("formation_A_latest", "")
    form_b = stats.get("formation_B_latest", "")

    # 1. Possession imbalance
    if abs(poss_a - poss_b) >= 8:
        trailing = "B" if poss_a > poss_b else "A"
        leading = "A" if trailing == "B" else "B"
        lead_poss = poss_a if leading == "A" else poss_b
        trail_poss = poss_b if leading == "A" else poss_a
        recs.append({
            "title": "Possession Recovery Strategy",
            "body": (
                f"Team {trailing} is being dominated in possession. Consider a higher pressing "
                f"line to win the ball earlier and disrupt Team {leading}'s build-up rhythm. "
                f"Prioritize safer midfield circulation after regains to reduce immediate turnovers."
            ),
            "citation": f"Possession: Team A {poss_a}% vs Team B {poss_b}%",
            "category": "tactical",
            "priority": "high" if abs(poss_a - poss_b) >= 15 else "medium",
        })

    # 2. Shot efficiency
    if shots_a + shots_b > 0:
        if shots_a != shots_b:
            trailing = "B" if shots_a > shots_b else "A"
            recs.append({
                "title": "Final-Third Chance Creation",
                "body": (
                    f"Team {trailing} is trailing in shot attempts. Focus on earlier ball "
                    f"progression into the final third through quick combination play or "
                    f"diagonal runs to increase shooting opportunities."
                ),
                "citation": f"Shots: Team A {shots_a} vs Team B {shots_b}",
                "category": "attacking",
                "priority": "high",
            })

        # Conversion rate analysis
        for team, shots, goals in [("A", shots_a, goals_a), ("B", shots_b, goals_b)]:
            if shots >= 3 and goals == 0:
                recs.append({
                    "title": f"Team {team} Shot Conversion Concern",
                    "body": (
                        f"Team {team} has generated {shots} shots but failed to convert. "
                        f"Consider working the ball into higher-quality positions closer to goal "
                        f"rather than attempting long-range efforts."
                    ),
                    "citation": f"Team {team}: {shots} shots, {goals} goals (0% conversion)",
                    "category": "attacking",
                    "priority": "high",
                })

    # 3. Formation stability
    total_shifts = shifts_a + shifts_b
    if total_shifts >= 2:
        more_shifts_team = "A" if shifts_a > shifts_b else "B"
        recs.append({
            "title": "Shape Stability & Compactness",
            "body": (
                f"Frequent formation shifts suggest unstable spacing, particularly for "
                f"Team {more_shifts_team}. Reinforce line compactness during transitions and "
                f"ensure the midfield block maintains consistent distances between lines."
            ),
            "citation": f"Formation shifts: Team A {shifts_a}, Team B {shifts_b}",
            "category": "tactical",
            "priority": "medium",
        })

    # 4. Sprint intensity
    if sprints_a + sprints_b > 0:
        higher = "A" if sprints_a > sprints_b else "B"
        lower = "B" if higher == "A" else "A"
        recs.append({
            "title": "Pressing & Counter-Press Intensity",
            "body": (
                f"Team {higher} is showing higher sprint intensity. Team {lower} should "
                f"increase off-ball running to match pressing triggers and prevent easy "
                f"progression through the midfield."
            ),
            "citation": (
                f"Sprints: Team A {sprints_a}, Team B {sprints_b}; "
                f"Total distance: Team A {dist_a}m, Team B {dist_b}m"
            ),
            "category": "physical",
            "priority": "medium",
        })

    # 5. Dribble analysis
    if dribbles_a + dribbles_b >= 2:
        more_dribbles = "A" if dribbles_a > dribbles_b else "B"
        other = "B" if more_dribbles == "A" else "A"
        recs.append({
            "title": "1v1 Duel Management",
            "body": (
                f"Team {more_dribbles} is winning more individual duels through dribbling. "
                f"Team {other} should consider double-marking key carriers or using a "
                f"cover-shadow defensive structure to limit 1v1 situations."
            ),
            "citation": f"Dribbles completed: Team A {dribbles_a}, Team B {dribbles_b}",
            "category": "defensive",
            "priority": "medium",
        })

    # 6. Possession changes / transitions
    if poss_changes_a + poss_changes_b >= 4:
        recs.append({
            "title": "Transition Efficiency",
            "body": (
                "High turnover frequency indicates a contested midfield battle. Both teams "
                "should focus on the first 3-5 seconds after winning the ball — either "
                "play forward quickly to exploit disorganized shape, or secure possession "
                "with a safe lateral pass."
            ),
            "citation": (
                f"Possession changes: Team A won {poss_changes_a}, Team B won {poss_changes_b}"
            ),
            "category": "tactical",
            "priority": "medium",
        })

    # Fallback if nothing triggered
    if not recs:
        recs.append({
            "title": "Balanced Contest",
            "body": (
                "Both teams are performing at comparable levels across key metrics. "
                "Focus on set-piece execution and second-ball recovery as differentiators."
            ),
            "citation": (
                f"Possession: {poss_a}%-{poss_b}%; Shots: {shots_a}-{shots_b}; "
                f"Sprints: {sprints_a}-{sprints_b}"
            ),
            "category": "tactical",
            "priority": "low",
        })

    return recs


# ---------------------------------------------------------------------------
# LLM-powered recommendations (OpenAI-compatible API)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are an elite football tactical analyst for MatchCast AI.
You receive real match statistics extracted from computer vision tracking data.

RULES:
1. Generate exactly 4-6 tactical recommendations.
2. Every recommendation MUST cite the specific stat(s) that justify it.
3. Be concrete and actionable — no vague generalities.
4. Cover different tactical dimensions: possession, pressing, attacking, defensive shape, physical output.
5. Address BOTH teams where relevant.
6. Output valid JSON: a list of objects with keys: "title", "body", "citation", "category", "priority".
   - category: one of "tactical", "attacking", "defensive", "physical", "set_piece"
   - priority: one of "high", "medium", "low"
7. Keep each body under 80 words. Keep each citation under 40 words.
8. Do NOT invent stats. Only reference numbers from the provided data."""


def _build_user_prompt(stats: dict[str, Any]) -> str:
    return (
        "Analyze the following match statistics and provide grounded tactical recommendations.\n\n"
        f"MATCH DATA:\n```json\n{json.dumps(stats, indent=2, default=str)}\n```"
    )


def _call_llm(stats: dict[str, Any]) -> Optional[list[dict]]:
    """Call OpenAI-compatible API. Returns parsed recommendations or None on failure."""
    api_key = GMI_CLOUD_API_KEY or GENBLAZE_API_KEY or os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("your-"):
        return None

    # Determine base URL — GMI Cloud uses a different endpoint
    base_url = os.getenv("LLM_BASE_URL", "")
    if not base_url:
        if GMI_CLOUD_API_KEY and not GMI_CLOUD_API_KEY.startswith("your-"):
            base_url = "https://api.gmi.ai/v1"
        else:
            base_url = "https://api.openai.com/v1"

    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    try:
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "model": model,
            "temperature": 0.4,
            "max_tokens": 2000,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(stats)},
            ],
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        content = body["choices"][0]["message"]["content"]

        # Extract JSON from possible markdown fences
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            content = json_match.group(1)

        parsed = json.loads(content.strip())
        if isinstance(parsed, list) and len(parsed) > 0:
            # Validate structure
            for item in parsed:
                if not all(k in item for k in ("title", "body", "citation")):
                    return None
                item.setdefault("category", "tactical")
                item.setdefault("priority", "medium")
            return parsed

    except Exception as e:
        print(f"[AI Coach] LLM call failed: {e}")

    return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def coach_status() -> dict:
    """Report whether the AI Coach can run."""
    api_key = GMI_CLOUD_API_KEY or GENBLAZE_API_KEY or os.getenv("OPENAI_API_KEY", "")
    has_key = bool(api_key) and not api_key.startswith("your-")
    return {
        "configured": has_key,
        "implemented": True,
        "mode": "llm" if has_key else "heuristic",
        "message": (
            "LLM credentials detected — AI Coach will generate grounded recommendations via LLM."
            if has_key
            else "No LLM key found. AI Coach will use heuristic analysis (still grounded in real stats). "
            "Add GMI_CLOUD_API_KEY, GENBLAZE_API_KEY, or OPENAI_API_KEY in .env for LLM mode."
        ),
    }


class AICoach:
    """Grounded tactical-recommendation generator."""

    def __init__(self) -> None:
        self.status = coach_status()

    def recommend(self, analytics: dict) -> dict:
        """
        Return grounded recommendations, each citing a stat.
        Tries LLM first, falls back to heuristic engine.
        """
        stats = aggregate_match_stats(analytics)
        mode = "heuristic"
        recommendations = None

        # Try LLM if configured
        if self.status["configured"]:
            recommendations = _call_llm(stats)
            if recommendations:
                mode = "llm"

        # Fallback to heuristic
        if not recommendations:
            recommendations = _heuristic_recommendations(stats)
            mode = "heuristic"

        # Compute performance scores
        poss_a = stats.get("possession_a", 50)
        shots_a = stats.get("events_by_team_type", {}).get("A", {}).get("shot", 0)
        shots_b = stats.get("events_by_team_type", {}).get("B", {}).get("shot", 0)
        score_a = max(6.5, min(9.4, 7.2 + ((poss_a - 50) / 30) + ((shots_a - shots_b) / 12)))
        score_b = max(6.5, min(9.4, 7.2 + ((50 - poss_a) / 30) + ((shots_b - shots_a) / 12)))

        return {
            "mode": mode,
            "recommendations": recommendations,
            "stats_summary": stats,
            "performance_scores": {
                "A": round(score_a, 1),
                "B": round(score_b, 1),
            },
        }
