# Creative Iteration Loop

Use this skill when improving an idea after scoring.

## Iteration Principles

- Optimize the weakest high-weight dimensions first:
  - visual impact
  - naked-eye 3D fit
  - spreadability
- Preserve the core idea if it already matches the brief.
- Do not solve every issue by adding complexity. Prefer a sharper visual mechanism over a longer script.
- If budget or timeline is tight, simplify production while keeping one strong spatial moment.
- If spreadability is weak, add a concrete audience action: photo angle, reveal moment, countdown, interaction cue, or location-specific surprise.
- If brand fit is weak, use recognizable assets, product behavior, brand metaphor, or media-side location context.

## Loop

1. Read the previous review.
2. Identify the top 3 score blockers.
3. Produce one improved version.
4. Re-score the improved version.
5. Stop when target score is reached or remaining risk is mainly external/missing brief data.

## Iteration Output

Each round should include:

- `round`
- `action`
- `score_before`
- `score_after`
- `score_delta`
- `focus`
- `summary`
- `agent_explanation`: explain why the change improved the idea in concrete creative, media, or production terms.
- `dimension_deltas`: list of changed rubric dimensions. Each item must include:
  - `key`
  - `name`
  - `score_before`
  - `score_after`
  - `delta`
  - `change`
  - `why`
- `key_improvements`: the most important positive dimension deltas for UI display.

Do not say only "the idea is stronger". Explain the mechanism. Example: `naked_eye_3d_fit +4 because the revision changed a flat product reveal into a screen-edge extrusion with foreground occlusion and stronger depth cues`.
