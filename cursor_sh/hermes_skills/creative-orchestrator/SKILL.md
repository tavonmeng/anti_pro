# Creative Orchestrator

Use this skill when a Hermes agent needs to generate, evaluate, and iterate commercial naked-eye 3D / outdoor LED creative concepts for Unique Vision.

## Operating Rules

- Treat the brief as the source of truth. Do not infer a missing brand, media location, budget, timeline, or screen form unless the brief clearly implies it.
- Do not modify orders, CRM records, customer documents, or production workflow state. The creative workbench is read-only against business objects.
- Use commercial creative judgment: the goal is a sellable, executable media idea, not pure visual appreciation.
- Prefer a few strong ideas over many thin ideas.
- Record why a creative decision improves score, feasibility, spreadability, or brand fit.
- If the designer provides `designer_direction` or `seed_ideas`, treat them as first-class creative intent. Preserve the core intent unless it conflicts with the brief, feasibility, or risk constraints; explain any deviation in the audit trace.

## Expected Workflow

1. Normalize the brief into:
   - project goal
   - brand/customer context
   - media location and viewing scene
   - screen shape, size, resolution, and 3D constraints
   - audience and emotional target
   - budget/timeline/hard constraints
2. Generate initial ideas.
3. Delegate independent review when `delegate_task` is available:
   - `rubric_evaluator`
   - `production_evaluator`
   - `risk_evaluator`
4. Use Python execution when available to aggregate scores and select the next iteration target.
5. Iterate until target score is reached or max rounds are exhausted.
6. Produce a ReAct-style audit trace using user-facing summaries only:
   - `plan`
   - `action`
   - `observation`
   - `reflection`
   - `decision`
7. Return strict JSON only.

## Output Quality

A good result must include:

- a clear concept sentence
- a naked-eye 3D spatial mechanism
- a screen-first visual beat or storyboard
- brand/media connection
- production notes
- risk notes
- a scored quality review
- iteration history
- ReAct-style audit steps that explain how the agent used tools, observations, scoring, and designer direction
- proposed team memory candidates when useful
