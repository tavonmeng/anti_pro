# Hermes Creative Skills

This directory contains the first Hermes skills for the admin creative workbench.

Configure Hermes to load this directory as an external skills path, then use the backend settings:

```env
HERMES_CREATIVE_PROFILE=creative-orchestrator
HERMES_CREATIVE_SKILLS_DIR=./hermes_skills
HERMES_CREATIVE_REQUIRED_TOOLSETS=skills,delegation,code_execution,memory,session_search
```

The backend still treats Hermes as a sidecar. Unique Vision stores sessions, ideas, reviews, iterations, events, and memory proposals in its own database. Hermes performs the agent work: skills, delegation, code execution, and long-running runs.
