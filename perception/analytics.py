"""
MatchCast AI — Phase 2 Analytics Module (Events & Formations)

Implements heuristic event detection (sprints, possession changes, shots,
dribbles) and formation-shift detection from tracking coordinates.
"""

import uuid
import numpy as np
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class MatchEvent(BaseModel):
    """Event occurring during the match."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = Field(..., description="Timestamp in seconds")
    type: str = Field(..., description="Event type: sprint, possession_change, shot, goal, assist, formation_shift")
    message: str = Field(..., description="Human-readable description of the event")
    team: Optional[str] = Field(None, description="Team associated with the event ('A', 'B', or None)")
    player_id: Optional[int] = Field(None, description="Player ID involved")
    details: Dict = Field(default_factory=dict, description="Additional context or metrics")


class MatchAnalytics(BaseModel):
    """Aggregated match analytics report."""
    match_id: str
    events: List[MatchEvent] = Field(default_factory=list)
    possession_a: float = Field(50.0, description="Possession percentage for Team A")
    possession_b: float = Field(50.0, description="Possession percentage for Team B")
    score_a: int = Field(0, description="Detected goals for Team A")
    score_b: int = Field(0, description="Detected goals for Team B")
    quality_flags: List[str] = Field(
        default_factory=list,
        description="Data-quality warnings for match-level event consistency",
    )
    player_stats: Dict[str, Dict] = Field(
        default_factory=dict,
        description="Stats per player: distance_meters, sprint_count, average_speed"
    )
    formations: Dict[str, List[Dict]] = Field(
        default_factory=dict,
        description="Formation timeline per team: {'A': [...], 'B': [...]}"
    )


class GameAnalyzer:
    """Runs heuristic analysis on a MatchTrackingData structure."""
    
    def __init__(self, tracking_data: dict):
        self.tracking_data = tracking_data
        self.match_id = tracking_data.get("match_id", "unknown")
        self.fps = float(tracking_data.get("fps", 25.0) or 25.0)
        self.frames = tracking_data.get("frames", [])

    @staticmethod
    def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
        return float(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))

    @staticmethod
    def _valid_team(team: Optional[str]) -> bool:
        return team in {"A", "B"}

    @staticmethod
    def _goal_line_for_team(team: str) -> float:
        # Team A attacks +x; Team B attacks -x.
        return 103.0 if team == "A" else 2.0

    @staticmethod
    def _team_attacking_direction(team: str) -> float:
        return 1.0 if team == "A" else -1.0

    @staticmethod
    def _infer_assist_player(
        touches: list[tuple[float, str, int]],
        goal_team: str,
        scorer_id: Optional[int],
        goal_time: float,
        lookback_sec: float = 12.0,
    ) -> Optional[int]:
        for t, team, pid in reversed(touches):
            if goal_time - t > lookback_sec:
                break
            if team != goal_team:
                continue
            if scorer_id is not None and pid == scorer_id:
                continue
            return pid
        return None

    @staticmethod
    def _scoreboard_consistency(events: list[MatchEvent]) -> tuple[int, int, list[str]]:
        """
        Derive score and flag suspicious event patterns.
        """
        goals = [e for e in events if e.type == "goal" and e.team in {"A", "B"}]
        shots = [e for e in events if e.type == "shot" and e.team in {"A", "B"}]

        score_a = sum(1 for e in goals if e.team == "A")
        score_b = sum(1 for e in goals if e.team == "B")
        flags: list[str] = []

        # Duplicate-goal guard: two goals by same team within 5 seconds is suspicious.
        for i in range(1, len(goals)):
            prev = goals[i - 1]
            cur = goals[i]
            if cur.team == prev.team and (cur.timestamp - prev.timestamp) <= 5.0:
                flags.append(
                    f"possible_duplicate_goal:{cur.team}:t={cur.timestamp:.2f}s"
                )

        # Missed-goal suspicion: many shots into box but no goals.
        box_pressure_a = sum(
            1
            for e in shots
            if e.team == "A" and float(e.details.get("ball_x", 0.0)) >= 95.0
        )
        box_pressure_b = sum(
            1
            for e in shots
            if e.team == "B" and float(e.details.get("ball_x", 105.0)) <= 10.0
        )

        if score_a == 0 and box_pressure_a >= 3:
            flags.append("possible_missed_goal:team=A")
        if score_b == 0 and box_pressure_b >= 3:
            flags.append("possible_missed_goal:team=B")

        # Assist consistency: every goal with known scorer should usually have a nearby assist candidate.
        assists = [e for e in events if e.type == "assist"]
        for g in goals:
            scorer = g.player_id
            if scorer is None:
                flags.append(f"goal_without_scorer:team={g.team}:t={g.timestamp:.2f}s")
                continue
            has_assist = any(
                a.team == g.team
                and a.player_id is not None
                and abs(a.timestamp - g.timestamp) <= 1.5
                for a in assists
            )
            if not has_assist:
                flags.append(f"goal_without_assist_candidate:team={g.team}:t={g.timestamp:.2f}s")

        # Keep output deterministic and compact.
        deduped_flags = sorted(set(flags))
        return score_a, score_b, deduped_flags

    @staticmethod
    def _normalize_line_counts(defenders: int, midfielders: int, attackers: int) -> tuple[int, int, int]:
        total = max(1, defenders + midfielders + attackers)

        d = int(round(defenders * 10 / total))
        m = int(round(midfielders * 10 / total))
        a = 10 - d - m

        d = min(6, max(2, d))
        m = min(6, max(2, m))
        a = 10 - d - m
        if a < 1:
            m = max(2, m + a - 1)
            a = 1

        return d, m, a

    @staticmethod
    def _formation_from_x_positions(team: str, x_values: list[float]) -> Optional[tuple[str, list[int]]]:
        if len(x_values) < 8:
            return None

        defenders = midfielders = attackers = 0
        for x in x_values:
            if team == "A":
                if x < 35:
                    defenders += 1
                elif x < 70:
                    midfielders += 1
                else:
                    attackers += 1
            else:
                if x > 70:
                    defenders += 1
                elif x > 35:
                    midfielders += 1
                else:
                    attackers += 1

        d, m, a = GameAnalyzer._normalize_line_counts(defenders, midfielders, attackers)
        return f"{d}-{m}-{a}", [d, m, a]

    def analyze(self) -> MatchAnalytics:
        """Run all analytics: distance, sprints, possession, shots, dribbles, and formations."""
        if not self.frames:
            return MatchAnalytics(match_id=self.match_id)

        events: list[MatchEvent] = []
        player_positions_history: dict[str, list[tuple[float, float, float, str]]] = {}

        # 1) Extract player histories (exclude referees/non-team rows)
        for frame_data in self.frames:
            t = frame_data.get("timestamp", 0.0)
            for player in frame_data.get("players", []):
                team = player.get("team")
                if not self._valid_team(team):
                    continue
                p_id = str(player["id"])
                if p_id not in player_positions_history:
                    player_positions_history[p_id] = []
                player_positions_history[p_id].append(
                    (
                        float(t),
                        float(player["pitch_x"]),
                        float(player["pitch_y"]),
                        str(team),
                    )
                )

        # 2) Player distances and sprints
        MIN_TRACK_POINTS = 8
        SPRINT_SPEED_THRESHOLD = 6.8
        SPRINT_MIN_DURATION = 0.8
        SPRINT_MIN_DISTANCE = 7.0
        SPRINT_COOLDOWN_SECS = 45.0
        player_last_sprint: dict[str, float] = {}

        player_stats = {}
        for p_id, history in player_positions_history.items():
            if len(history) < MIN_TRACK_POINTS:
                continue

            total_distance = 0.0
            sprint_count = 0
            speeds = []
            is_sprinting = False
            sprint_start_t = 0.0
            sprint_distance = 0.0
            sprint_speed_samples: list[float] = []
            team = history[0][3]

            for i in range(1, len(history)):
                t1, x1, y1, _ = history[i - 1]
                t2, x2, y2, _ = history[i]
                dt = t2 - t1
                if dt <= 0:
                    continue

                dist = self._distance(x1, y1, x2, y2)
                total_distance += dist
                speed = dist / dt
                speeds.append(speed)

                if speed >= SPRINT_SPEED_THRESHOLD:
                    if not is_sprinting:
                        is_sprinting = True
                        sprint_start_t = t2
                        sprint_distance = dist
                        sprint_speed_samples = [speed]
                    else:
                        sprint_distance += dist
                        sprint_speed_samples.append(speed)
                else:
                    if is_sprinting:
                        is_sprinting = False
                        sprint_dur = t2 - sprint_start_t
                        last_sprint = player_last_sprint.get(p_id, -9999)
                        cooldown_ok = (sprint_start_t - last_sprint) >= SPRINT_COOLDOWN_SECS
                        if (
                            sprint_dur >= SPRINT_MIN_DURATION
                            and sprint_distance >= SPRINT_MIN_DISTANCE
                            and cooldown_ok
                        ):
                            sprint_count += 1
                            player_last_sprint[p_id] = sprint_start_t
                            top_speed = float(max(sprint_speed_samples or [speed]))
                            events.append(MatchEvent(
                                timestamp=sprint_start_t,
                                type="sprint",
                                message=(
                                    f"High-intensity sprint — Player #{p_id} (Team {team}), "
                                    f"top speed {top_speed:.1f} m/s ({top_speed * 3.6:.0f} km/h)"
                                ),
                                team=team,
                                player_id=int(p_id),
                                details={
                                    "top_speed_mps": round(top_speed, 2),
                                    "duration_sec": round(sprint_dur, 1),
                                    "distance_m": round(sprint_distance, 1),
                                }
                            ))

            avg_speed = np.mean(speeds) if speeds else 0.0
            player_stats[p_id] = {
                "distance_meters": round(total_distance, 1),
                "sprint_count": sprint_count,
                "average_speed_mps": round(float(avg_speed), 2),
                "team": team,
            }

        # 3) Possession, shots, and dribbles
        POSSESSION_RADIUS = 2.5
        POSSESSION_CONFIRM_SECONDS = 1.0
        POSSESSION_CHANGE_COOLDOWN = 8.0
        SHOT_COOLDOWN = 12.0
        SHOT_MIN_SPEED = 14.0
        DRIBBLE_COOLDOWN = 15.0
        DRIBBLE_SIGN_CHANGES = 3

        possession_a_time = 0.0
        possession_b_time = 0.0
        current_possessor_team = None
        current_possessor_id: Optional[int] = None
        candidate_possessor_team = None
        candidate_possessor_id: Optional[int] = None
        candidate_since = 0.0
        last_possession_event_t = -9999.0
        last_shot_event_t = -9999.0
        last_dribble_event_t = -9999.0
        last_goal_event_t = -9999.0

        GOAL_CONFIRM_WINDOW_SEC = 3.0
        GOAL_EVENT_COOLDOWN_SEC = 8.0

        recent_touches: list[tuple[float, str, int]] = []
        shot_candidates: list[dict] = []

        ball_dx_window: list[float] = []
        last_ball_x = None
        last_ball_y = None
        last_ball_t = None
        last_ball_holder_id: Optional[int] = None

        prev_ts = float(self.frames[0].get("timestamp", 0.0))
        for frame_data in self.frames:
            t = float(frame_data.get("timestamp", 0.0))
            dt_frame = max(0.0, t - prev_ts)
            prev_ts = t

            ball = frame_data.get("ball")
            players = frame_data.get("players", [])

            if not ball or not players:
                continue

            bx, by = ball["pitch_x"], ball["pitch_y"]

            # Find closest non-referee player to ball
            closest_player = None
            min_dist = float("inf")
            for player in players:
                p_team = player.get("team")
                if not self._valid_team(p_team):
                    continue
                px, py = player["pitch_x"], player["pitch_y"]
                dist = self._distance(px, py, bx, by)
                if dist < min_dist:
                    min_dist = dist
                    closest_player = player

            # Possession state machine with confirmation window
            if min_dist <= POSSESSION_RADIUS and closest_player:
                p_id = closest_player["id"]
                p_team = closest_player["team"]

                if p_team != candidate_possessor_team:
                    candidate_possessor_team = p_team
                    candidate_possessor_id = int(p_id)
                    candidate_since = t

                if (
                    candidate_possessor_team is not None
                    and (t - candidate_since) >= POSSESSION_CONFIRM_SECONDS
                    and (
                        candidate_possessor_team != current_possessor_team
                        or candidate_possessor_id != current_possessor_id
                    )
                ):
                    current_possessor_team = candidate_possessor_team
                    current_possessor_id = candidate_possessor_id
                    if current_possessor_id is not None:
                        recent_touches.append((t, current_possessor_team, int(current_possessor_id)))
                        # Keep only recent touch history to bound memory.
                        cutoff = t - 25.0
                        recent_touches = [x for x in recent_touches if x[0] >= cutoff]

                    if (t - last_possession_event_t) >= POSSESSION_CHANGE_COOLDOWN:
                        last_possession_event_t = t
                        events.append(MatchEvent(
                            timestamp=t,
                            type="possession_change",
                            message=(
                                f"Possession won by Team {p_team} — "
                                f"Player #{p_id} takes control in the "
                                f"{'attacking' if (bx > 52.5 and p_team == 'A') or (bx < 52.5 and p_team == 'B') else 'defensive'} half"
                            ),
                            team=p_team,
                            player_id=int(p_id),
                        ))

                last_ball_holder_id = int(p_id)

            if current_possessor_team == "A":
                possession_a_time += dt_frame
            elif current_possessor_team == "B":
                possession_b_time += dt_frame

            # Ball movement based event detection
            if last_ball_x is not None and last_ball_t is not None:
                dt = t - last_ball_t
                if dt > 0:
                    dx = bx - last_ball_x
                    dy = by - last_ball_y
                    ball_speed = self._distance(0.0, 0.0, dx, dy) / dt

                    # Shot detection
                    if ball_speed >= SHOT_MIN_SPEED and (t - last_shot_event_t) >= SHOT_COOLDOWN:
                        shot_team = current_possessor_team
                        if shot_team is None:
                            shot_team = "A" if dx > 0 else "B"

                        if shot_team == "A" and bx >= 83.0 and dx > 0:
                            last_shot_event_t = t
                            zone = "right side" if by > 34 else "left side"
                            events.append(MatchEvent(
                                timestamp=t,
                                type="shot",
                                message=f"Shot on goal! Team A drives the ball toward Team B's net ({zone})",
                                team="A",
                                player_id=last_ball_holder_id,
                                details={
                                    "ball_x": round(float(bx), 1),
                                    "ball_y": round(float(by), 1),
                                    "ball_speed_mps": round(float(ball_speed), 1),
                                }
                            ))
                            shot_candidates.append(
                                {
                                    "team": "A",
                                    "timestamp": t,
                                    "shooter_id": last_ball_holder_id,
                                }
                            )
                        elif shot_team == "B" and bx <= 22.0 and dx < 0:
                            last_shot_event_t = t
                            zone = "right side" if by > 34 else "left side"
                            events.append(MatchEvent(
                                timestamp=t,
                                type="shot",
                                message=f"Shot on goal! Team B drives the ball toward Team A's net ({zone})",
                                team="B",
                                player_id=last_ball_holder_id,
                                details={
                                    "ball_x": round(float(bx), 1),
                                    "ball_y": round(float(by), 1),
                                    "ball_speed_mps": round(float(ball_speed), 1),
                                }
                            ))
                            shot_candidates.append(
                                {
                                    "team": "B",
                                    "timestamp": t,
                                    "shooter_id": last_ball_holder_id,
                                }
                            )

                    # Goal detection from shot outcome near end line.
                    active_candidates = [
                        c for c in shot_candidates if 0.0 <= (t - float(c["timestamp"])) <= GOAL_CONFIRM_WINDOW_SEC
                    ]
                    shot_candidates = active_candidates
                    for candidate in list(active_candidates):
                        team = str(candidate["team"])
                        direction = self._team_attacking_direction(team)
                        goal_line = self._goal_line_for_team(team)
                        crossed = (bx >= goal_line) if team == "A" else (bx <= goal_line)
                        moving_to_goal = (dx * direction) > 0

                        if crossed and moving_to_goal and (t - last_goal_event_t) >= GOAL_EVENT_COOLDOWN_SEC:
                            scorer_id = candidate.get("shooter_id")
                            if scorer_id is None:
                                scorer_id = last_ball_holder_id

                            goal_event = MatchEvent(
                                timestamp=t,
                                type="goal",
                                message=f"GOAL! Team {team} scores.",
                                team=team,
                                player_id=int(scorer_id) if scorer_id is not None else None,
                                details={
                                    "ball_x": round(float(bx), 2),
                                    "ball_y": round(float(by), 2),
                                    "from_shot_ts": round(float(candidate["timestamp"]), 2),
                                },
                            )
                            events.append(goal_event)
                            last_goal_event_t = t

                            assister_id = self._infer_assist_player(
                                touches=recent_touches,
                                goal_team=team,
                                scorer_id=int(scorer_id) if scorer_id is not None else None,
                                goal_time=t,
                            )
                            if assister_id is not None:
                                events.append(MatchEvent(
                                    timestamp=max(0.0, t - 0.01),
                                    type="assist",
                                    message=f"Assist by Player #{assister_id} (Team {team}).",
                                    team=team,
                                    player_id=int(assister_id),
                                    details={
                                        "goal_timestamp": round(float(t), 2),
                                        "scorer_id": int(scorer_id) if scorer_id is not None else None,
                                    },
                                ))

                            if candidate in shot_candidates:
                                shot_candidates.remove(candidate)
                            break

                    # Dribble detection by short-term direction changes while in control
                    ball_dx_window.append(dx)
                    if len(ball_dx_window) > 8:
                        ball_dx_window.pop(0)

                    sign_changes = sum(
                        1
                        for i in range(1, len(ball_dx_window))
                        if ball_dx_window[i] * ball_dx_window[i - 1] < 0
                    )
                    if (
                        sign_changes >= DRIBBLE_SIGN_CHANGES
                        and min_dist < 2.5
                        and closest_player is not None
                        and last_ball_holder_id is not None
                        and int(closest_player["id"]) == int(last_ball_holder_id)
                        and 1.5 <= ball_speed <= 9.5
                        and (t - last_dribble_event_t) >= DRIBBLE_COOLDOWN
                    ):
                        last_dribble_event_t = t
                        p_id = closest_player["id"]
                        p_team = closest_player["team"]
                        events.append(MatchEvent(
                            timestamp=t,
                            type="dribble",
                            message=(
                                f"Dribble! Player #{p_id} (Team {p_team}) beats pressure "
                                f"near x={bx:.0f}m, y={by:.0f}m"
                            ),
                            team=p_team,
                            player_id=int(p_id),
                            details={"ball_x": round(float(bx), 1), "ball_y": round(float(by), 1)},
                        ))

            last_ball_x = bx
            last_ball_y = by
            last_ball_t = t

        # Possession percentages from controlled-ball time
        total_poss_time = possession_a_time + possession_b_time
        pos_a = round((possession_a_time / total_poss_time) * 100, 1) if total_poss_time > 0 else 50.0
        pos_b = round(100 - pos_a, 1)

        # 4) Formation timeline + shift events (30s windows)
        formations = {"A": [], "B": []}
        window_sec = 30.0
        window_buckets: dict[int, dict[str, list[float]]] = {}
        for fr in self.frames:
            t = float(fr.get("timestamp", 0.0))
            bucket_idx = int(t // window_sec)
            if bucket_idx not in window_buckets:
                window_buckets[bucket_idx] = {"A": [], "B": []}
            for p in fr.get("players", []):
                team = p.get("team")
                if not self._valid_team(team):
                    continue
                window_buckets[bucket_idx][team].append(float(p.get("pitch_x", 0.0)))

        previous_lines = {"A": None, "B": None}
        for bucket_idx in sorted(window_buckets.keys()):
            window_start = bucket_idx * window_sec
            team_x_window = window_buckets[bucket_idx]

            for team in ("A", "B"):
                formation = self._formation_from_x_positions(team, team_x_window[team])
                if formation is None:
                    continue

                formation_str, line_counts = formation
                formations[team].append(
                    {
                        "timestamp": round(window_start, 1),
                        "formation": formation_str,
                        "line_counts": line_counts,
                    }
                )

                prev = previous_lines[team]
                if prev is not None:
                    delta = int(sum(abs(line_counts[i] - prev[i]) for i in range(3)))
                    if delta >= 3:
                        events.append(MatchEvent(
                            timestamp=round(window_start, 1),
                            type="formation_shift",
                            message=(
                                f"Team {team} shape changed: "
                                f"{prev[0]}-{prev[1]}-{prev[2]} -> {formation_str}"
                            ),
                            team=team,
                            details={
                                "from": prev,
                                "to": line_counts,
                                "delta": delta,
                                "window_seconds": int(window_sec),
                            },
                        ))
                previous_lines[team] = line_counts

        # Sort events chronologically
        events.sort(key=lambda x: x.timestamp)

        score_a, score_b, quality_flags = self._scoreboard_consistency(events)

        return MatchAnalytics(
            match_id=self.match_id,
            events=events,
            possession_a=pos_a,
            possession_b=pos_b,
            score_a=score_a,
            score_b=score_b,
            quality_flags=quality_flags,
            player_stats=player_stats,
            formations=formations,
        )
