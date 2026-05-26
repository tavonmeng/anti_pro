# Creative Rubric Evaluator

Use this skill when scoring a Unique Vision creative idea against the commercial creative quality rubric.

## Rubric

Total score: 100.

- `goal_fit`, 10: Does the idea directly serve the campaign/media objective?
- `visual_impact`, 15: Is the first-view visual strong, legible, and memorable?
- `naked_eye_3d_fit`, 15: Does it use depth, extrusion, occlusion, perspective, or screen-edge illusion in a way that fits the actual screen?
- `spreadability`, 15: Is there a social hook, photo/video moment, surprise, or discussion trigger?
- `brand_asset_fit`, 10: Does it connect to brand/customer/media assets instead of feeling generic?
- `execution_feasibility`, 10: Can it be produced with plausible assets, time, screen specs, and technical constraints?
- `cost_benefit`, 10: Is the impact worth the production complexity and cost?
- `originality`, 8: Is it differentiated from common 3D billboard tropes?
- `emotional_power`, 5: Does it create a clear emotion?
- `compliance_risk`, 2: Is it low risk for public display, brand safety, and factual claims?

## Scoring Rules

- Be strict but constructive.
- Every dimension must include `score`, `max`, and `reason`.
- Do not give high naked-eye 3D scores to concepts that only describe a normal 2D animation.
- Do not give high feasibility scores when key screen specs or assets are missing.
- If the brief lacks essential details, reflect that in the score and recommendations.

## Review Output

Return a review object with:

- `rubric_version`
- `scores`
- `total_score`
- `grade`
- `core_issues`
- `recommendations`
- `risk_flags`
- `summary`
