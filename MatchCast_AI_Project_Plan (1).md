# MatchCast AI — Project Plan & Task Division

**Match Intelligence & Generative Media Platform for Amateur Sports**
Backblaze Generative Media Hackathon (Genblaze + B2)

**Team size:** 3
**Planning date:** July 14, 2026
**Target completion:** August 1, 2026 (18 days, built-in buffer before the official Aug 3 deadline)

---

## 1. Project Summary

Amateur and school sports teams have no access to the analysis, highlight production, or coaching insight that professional teams get from dedicated staff. MatchCast AI turns a single video of an amateur match into:

- A structured tracking dataset (player positions, IDs, events)
- An AI-generated highlight reel with commentary, voiceover, and tactical graphics
- AI Coach recommendations grounded in real match data
- Per-player performance summaries
- A top-down "radar view" tactical replay

Every feature is a different view onto **one shared data source** — the tracking dataset produced in Phase 1 — rather than separate disconnected subsystems. This keeps the build coherent and lets the team parallelize cleanly.

---

## 2. System Architecture

```
                    ┌─────────────────────────┐
                    │   Uploaded Match Video   │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │   PERCEPTION LAYER        │
                    │   YOLO + ByteTrack        │
                    │   Homography calibration  │
                    │   Event/formation heuristics│
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Structured Match Dataset │
                    │  (positions, IDs, events, │
                    │   formations, timestamps) │
                    └──┬─────────────┬─────────┘
                       │             │
         ┌─────────────▼───┐   ┌─────▼──────────────┐
         │ INTELLIGENCE     │   │ GENERATIVE LAYER    │
         │ LAYER            │   │ (Genblaze)          │
         │ - AI Coach       │   │ - Commentary text    │
         │ - Player summaries│  │ - Voiceover/TTS      │
         │ - Radar replay   │   │ - Multilingual audio │
         └─────────────┬───┘   │ - Tactical graphics  │
                       │       │ - Highlight assembly  │
                       │       │ - Social content       │
                       │       └─────────┬──────────────┘
                       │                 │
                    ┌──▼─────────────────▼───┐
                    │   Streamlit Frontend     │
                    │   (dashboard + player)   │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │   Backblaze B2 Storage    │
                    │   raw video → tracking →  │
                    │   generated assets, per   │
                    │   match, versioned        │
                    └─────────────────────────┘
```

---

## 3. Feature Scope (What's In / What's Cut)

Features are grouped into four tiers so the team always knows what to protect first and what to cut first if time runs short. **Tier order is priority order: never start a Tier 2 item before every Tier 1 exit criterion is met, and never start Tier 3 before Tier 2 is solid.**

### Tier 1 — Core (non-negotiable, must work end to end)

| Feature | Notes |
|---|---|
| Player detection & tracking | YOLO + ByteTrack |
| Homography / pitch calibration | Manual reference points, fixed/semi-fixed camera |
| Formation-change detection | Heuristic (positional clustering), not a trained classifier |
| Top-down radar replay | Derived directly from real tracking data; strong fallback demo on its own |
| Key match statistics | Possession-adjacent counts, shots, formation shifts — derived from the tracking dataset |
| AI-generated commentary + report | LLM over real extracted events |
| Voiceover / TTS | Synced to highlight clips |
| Highlight reel auto-assembly | Clips + commentary + graphics + voiceover |
| AI Coach recommendations | LLM grounded in real match stats, **with explicit citation of the positions/events/stats behind each recommendation** — this is now a core requirement, not a polish item, since it's cheap to add on top of Phase 4 and directly strengthens the "one shared dataset" pitch |

**This tier alone must be a complete, demoable product.** Nothing below this line matters if Tier 1 isn't solid.

### Tier 2 — Cheap enhancements (add only once Tier 1 exit criteria are met)

| Feature | Notes |
|---|---|
| Smart Match Timeline | Clickable list of key events (goals, shots, cards, formation shifts) that jump the video/radar to that moment. Pure UI layer over data already produced in Phase 1/2 — low risk, high demo value. |

### Tier 3 — True stretch (Phase 5 only, cut first if behind schedule)

| Feature | Notes |
|---|---|
| AI Match Chat | Scoped strictly to **filterable/aggregation queries over structured data** ("show every attack from the left side," "compare first and second half stats") — NOT open causal questions like "why did we lose," which risk confident-sounding but unfounded answers under judge questioning. If causal-style questions are asked, the answer surfaces correlated stats rather than claiming causation. |
| Heatmaps | Density plots from existing tracked positions — cheap given the dataset already exists |
| Momentum graph | Approximated from event density / proximity-to-goal over time, using data already extracted |
| Highlight video polish | Auto-added player cards, tactical graphic overlays, and a short auto-generated match summary at the intro — incremental extension of Phase 3, not a new subsystem |
| Multilingual commentary | Translate text + regenerate voice per language |
| Personalized per-player highlights | Requires reliable player ID filtering |
| Player performance summaries ("scouting," reframed) | Movement stats + LLM qualitative summary. Explicitly NOT framed as talent discovery/prediction |
| Social media content generation | Repurposes existing generated assets |

### Tier 4 — Cut (mention as future roadmap only, do not build)

| Feature | Notes |
|---|---|
| Passing network | Requires reliable pass/possession detection, which is a new, unvalidated CV problem outside current perception scope — same category of risk as the other cut items below |
| Digital Twin / performance prediction | No validated predictive basis achievable in scope |
| What-If tactical simulation | Predictive version unachievable; non-predictive drag-and-drop sandbox is a future-roadmap mention only |
| Injury risk prediction | No validated data/outcome pairing possible from video alone |
| Referee AI / decision review | Requires multi-camera calibrated systems (VAR-class problem), out of scope |

Tier 4 features are appropriate to mention as **future roadmap** in the pitch, not as built functionality.

---

## 4. Timeline (July 14 – August 1)

### Phase 1 — Perception Foundation (July 14–20, 7 days)
Detection, tracking, homography calibration on sample clips.
**Exit criteria:** clean, reliable pitch-coordinate output for a full test clip.

### Phase 2 — Events, Formations, Radar Replay (July 20–24, 4 days)
Heuristic event/formation-change detection; radar-view visualization; Smart Match Timeline (clickable events that jump to the corresponding video/radar moment) built as a thin UI layer on top of this same event data.
**Exit criteria:** formation-change detection works and the radar replay looks good — this is the safety-net demo even if later phases slip.

### Phase 3 — Generative Pipeline (July 24–28, 4 days)
Genblaze integration: commentary generation → voiceover → tactical graphics → highlight assembly. B2 storage wired in throughout, not bolted on at the end.
**Exit criteria:** one fully generated highlight reel, end to end, stored and retrievable from B2.

### Phase 4 — Intelligence Layer (July 28–30, 2 days)
AI Coach recommendations, player performance summaries.
**Exit criteria:** outputs read as genuinely grounded in real match data, not generic filler text. Specifically, every AI Coach recommendation must cite the concrete positions, events, or stats that led to it — this explainability requirement is core, not optional polish.

### Phase 5 — Stretch Features + Polish (July 30 – Aug 1, 2 days)
Tier 3 stretch features, attempted in this priority order — **only if Phases 1–4 are solid,** and cut ruthlessly from the bottom of this list if behind schedule:
1. Heatmaps / momentum graph (cheapest — reuse existing tracking data)
2. Highlight video polish (player cards, tactical graphic overlays, intro summary)
3. AI Match Chat (scoped to filterable/aggregation queries only, not open causal questions)
4. Multilingual commentary, personalized highlights, player performance summaries, social content

Final: demo video, Devpost write-up, submission polish.

**Buffer:** Aug 1 target leaves Aug 2–3 as slack before the actual deadline for bug fixes and submission issues.

---

## 5. Task Division (3 Members)

### Member A — Perception & Computer Vision Engineer
Owns Phase 1 end to end; supports Phase 2.

- YOLO fine-tuning for player/ball detection (SoccerNet or Roboflow football datasets)
- ByteTrack integration for consistent player IDs
- Homography calibration workflow (reference-point marking, coordinate transform)
- Outputs the core structured dataset (positions, IDs, timestamps) that every other feature consumes
- Supports Member C on formation-change heuristics (owns the CV side of "what counts as a formation shift")

### Member B — Generative AI & Backend Engineer
Owns Phase 3 end to end; supports Phase 4.

- Genblaze orchestration pipeline: commentary generation → TTS voiceover → tactical graphic generation → video assembly
- Multilingual commentary pipeline (stretch)
- B2 storage integration: raw video, tracking data, generated assets, versioning per match
- AI Coach prompt design and LLM integration (Phase 4, grounded in Member A's structured dataset, with mandatory citation of the specific data behind each recommendation)
- AI Match Chat backend: query parsing over the structured dataset, strictly scoped to filterable/aggregation questions (stretch, Phase 5)

### Member C — Frontend, Integration & Product Lead
Owns Phase 2 visualization; owns integration and delivery throughout.

- Streamlit dashboard: video upload, radar-view replay, highlight reel player, coach recommendations display (with citations)
- Formation-change visualization logic (working with Member A's heuristics)
- Smart Match Timeline: clickable event list that jumps to the corresponding video/radar moment (Phase 2, core)
- AI Match Chat UI, scoped to filterable/aggregation queries only (stretch, Phase 5)
- Player performance summary UI (stretch)
- Social content generation UI (stretch)
- Integration testing across all three layers as pieces land
- Demo video, Devpost write-up, and submission packaging (Phase 5)

### Shared responsibilities
- **Daily 15-minute sync** to catch integration mismatches early (Member A's output format is Member B's and C's input — keep this contract stable and agreed from day 1).
- All three review the final Devpost write-up together before submission — especially the limitations/roadmap section, so cut features are framed honestly as future direction.

---

## 6. Risk Notes

- **Biggest risk: homography calibration quality.** If Phase 1 slips, everything downstream slips. Start here immediately, and keep Phase 2's radar replay as a strong fallback demo even if generative features aren't fully polished.
- **Second risk: Genblaze pipeline reliability under time pressure.** Build Phase 3 with graceful fallbacks (e.g., if voiceover generation fails, still show generated text commentary) so a partial failure doesn't break the whole demo.
- **Keep claims honest in the submission:** "near real-time," not "real-time"; "heuristic formation detection," not "trained tactical AI"; "performance summary," not "talent discovery/prediction." This protects credibility under judge questioning far more than a flashier claim would.
- **Scope discipline is a risk-management tool, not just a nice-to-have.** A complete, polished Tier 1 demo beats a longer feature list with rough edges — both for reliability under time pressure and for credibility with judges. If a Tier 3 feature isn't solid by the time its slot in Phase 5 runs out, cut it rather than ship it half-working.

---

## 7. Next Steps

1. Member A starts dataset sourcing (SoccerNet / Roboflow) and YOLO fine-tuning immediately.
2. Member B sets up Genblaze API access and drafts the commentary/voiceover prompt chain.
3. Member C scaffolds the Streamlit app shell and B2 bucket structure so both other members can plug into a stable interface from day one.
