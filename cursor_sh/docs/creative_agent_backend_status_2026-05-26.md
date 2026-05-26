# Creative Agent Backend Status - 2026-05-26

## 当前目标

为管理员端创意团队增加一个基于 Hermes Agent 的创意工作台后端。该 Agent 不接入用户下单流程，不修改订单，只读取 brief / 订单信息，生成创意、按质检标准评分、自动迭代，并支持设计师中途介入后继续迭代。

## Hermes 接入方式

当前是通过 Hermes API Server 调用，不修改 Hermes 源码。

后端调用：

- `POST /v1/runs`
- `GET /v1/runs/{run_id}`
- `GET /v1/runs/{run_id}/events`
- `POST /v1/runs/{run_id}/stop`

本项目新增了外部 Hermes skills：

- `cursor_sh/hermes_skills/creative-orchestrator/SKILL.md`
- `cursor_sh/hermes_skills/creative-rubric-evaluator/SKILL.md`
- `cursor_sh/hermes_skills/creative-iteration-loop/SKILL.md`

后端配置项已加入：

- `HERMES_AGENT_ENABLED`
- `HERMES_API_BASE_URL`
- `HERMES_API_KEY`
- `HERMES_MODEL_NAME`
- `HERMES_HTTP_TIMEOUT`
- `HERMES_CREATIVE_PROFILE`
- `HERMES_CREATIVE_SKILLS_DIR`
- `HERMES_CREATIVE_REQUIRED_TOOLSETS`
- `HERMES_CREATIVE_BACKGROUND_TIMEOUT`
- `HERMES_CREATIVE_POLL_INTERVAL`

## 已完成能力

1. 创意会话

- 支持手动创建会话。
- 支持从订单只读生成 brief。
- 支持团队/个人可见性。
- 支持 `designer_direction`，用于设计师大概创意方向。
- 支持 `seed_ideas`，用于设计师粗想法或初始方向。

2. 创意方案

- Agent 可以生成多版方案。
- 设计师可以手动保存一个方案。
- 方案包含：
  - title
  - core_concept
  - spatial_mechanism
  - story_outline
  - production_notes
  - risk_notes
  - tags
  - score

3. 创意质检

质检标准来自 `创意调试—Agent质检idea(1).docx`：

- 目标匹配度 10
- 视觉冲击力 15
- 裸眼3D适配度 15
- 传播性 15
- 品牌资产关联度 10
- 执行可行性 10
- 成本收益比 10
- 原创性与差异化 8
- 情绪感染力 5
- 合规与风险 2

4. 自动迭代

- 支持 `auto-run`：从 brief / designer_direction / seed_ideas 出发自动生成、评估、迭代。
- 支持对单个 idea 执行 `evaluate`。
- 支持对单个 idea 执行 `iterate`。
- 迭代记录会保存：
  - score_before
  - score_after
  - score_delta
  - dimension_deltas
  - key_improvements
  - agent_explanation

这样前端可以展示“哪个维度涨了、涨了多少、为什么涨”。

5. ReAct-style 可审计步骤

新增 `creative_agent_steps`，保存面向用户的 ReAct-style 摘要，不保存模型隐藏思考链。

阶段包括：

- plan
- action
- observation
- reflection
- decision

每步可保存：

- role
- tool_name
- input_summary
- output_summary
- observation
- reflection_summary
- decision
- next_action
- score_snapshot
- dimension_deltas

6. 设计师中途介入

新增 `creative_designer_feedbacks`。

设计师可以在几轮迭代后提交反馈，反馈会作为下一轮迭代的 state patch，而不是普通评论。

支持字段：

- feedback_text
- priority
- constraints
- liked_parts
- disliked_parts
- requested_changes
- target_idea_id
- run_id

然后通过 `continue-run` 启动下一轮 Hermes 迭代。后端会把以下信息一起传给 Hermes：

- brief
- designer_direction
- seed_ideas
- target_idea
- designer_feedback
- recent_iterations
- recent_agent_steps
- target_idea_reviews
- recent_designer_feedbacks
- team_memory
- personal_memory

7. Memory

新增创意团队 memory：

- team
- personal
- project

Agent 输出的 `team_memory_candidates` 会以 `proposed` 状态保存，后续前端可审核。

## 新增/修改文件

后端新增：

- `cursor_sh/backend/app/api/creative_agent.py`
- `cursor_sh/backend/app/models/creative_agent.py`
- `cursor_sh/backend/app/schemas/creative_agent.py`
- `cursor_sh/backend/app/services/creative_agent_service.py`
- `cursor_sh/backend/app/services/hermes_client.py`
- `cursor_sh/backend/scripts/migrate_creative_agent_iterations.py`
- `cursor_sh/backend/scripts/migrate_creative_agent_react.py`
- `cursor_sh/backend/scripts/migrate_creative_designer_feedbacks.py`

后端修改：

- `cursor_sh/backend/app/config.py`
- `cursor_sh/backend/app/main.py`
- `cursor_sh/backend/app/models/__init__.py`
- `cursor_sh/backend/.env.example`

Hermes skills 新增：

- `cursor_sh/hermes_skills/README.md`
- `cursor_sh/hermes_skills/creative-orchestrator/SKILL.md`
- `cursor_sh/hermes_skills/creative-rubric-evaluator/SKILL.md`
- `cursor_sh/hermes_skills/creative-iteration-loop/SKILL.md`

## API 概览

Base path: `/api/admin/creative-agent`

Hermes:

- `GET /hermes/status`

订单 brief：

- `GET /orders/{order_id}/brief`

会话：

- `GET /sessions`
- `POST /sessions`
- `GET /sessions/{session_id}`
- `PATCH /sessions/{session_id}`

运行：

- `POST /sessions/{session_id}/auto-run`
- `GET /runs/{run_id}`
- `POST /runs/{run_id}/refresh`
- `POST /runs/{run_id}/stop`
- `GET /runs/{run_id}/events`
- `GET /runs/{run_id}/events/stream`
- `GET /runs/{run_id}/steps`

方案：

- `POST /sessions/{session_id}/ideas`
- `POST /ideas/{idea_id}/evaluate`
- `POST /ideas/{idea_id}/iterate`

设计师反馈 / 人类介入：

- `GET /sessions/{session_id}/feedbacks`
- `POST /sessions/{session_id}/feedbacks`
- `POST /sessions/{session_id}/continue-run`

Memory:

- `GET /memory`
- `POST /memory`
- `PATCH /memory/{entry_id}`

## 数据表

新增表：

- `creative_sessions`
- `creative_ideas`
- `creative_reviews`
- `creative_runs`
- `creative_run_events`
- `creative_agent_steps`
- `creative_iterations`
- `creative_designer_feedbacks`
- `creative_memory_entries`

## 已验证

已运行：

```bash
venv/bin/python -m compileall app scripts/migrate_creative_designer_feedbacks.py scripts/migrate_creative_agent_react.py scripts/migrate_creative_agent_iterations.py
venv/bin/python -c "from app.main import app; print('routes', len(app.routes))"
venv/bin/python -c "from app.database import Base; import app.models; print([n for n in sorted(Base.metadata.tables) if n.startswith('creative_')])"
```

验证结果：

- app 正常加载。
- 当前路由数：143。
- creative 相关表已注册。

## 当前未完成

1. 前端还未开发

管理员界面还没有接这些后端 API。建议下一步做：

- 创意工作台入口
- session list
- brief editor
- designer direction / seed ideas 输入
- idea version chain
- review score panel
- iteration dimension delta 展示
- ReAct steps timeline
- designer feedback and continue-run 面板

2. Hermes sidecar 尚未真实联调

后端代码按官方 Runs API 接好，但还没有在本地真实启动 Hermes gateway 做端到端测试。

3. Hermes 源码未修改

当前完全是外部 API 接入。若后续要改 Hermes 源码，推荐只改通用 runtime 能力：

- structured ReAct events
- pause/resume
- state_patch
- schema validation/retry
- tool permission policy

不要把创意业务逻辑写进 Hermes core。

## 当前 git 工作区注意事项

当前有无关或既有变更：

- `.DS_Store` 被修改
- `PLATFORM SERVICES.docx` 未跟踪

这些不是本次创意 Agent 后端开发的核心改动，切分支或提交时注意不要误带。

## 建议下一步

如果继续当前功能，优先开发前端：

1. 管理员侧新增 `CreativeLab.vue`
2. sidebar/router 加入口
3. 接 session / auto-run / run polling
4. 展示 score table 和 dimension deltas
5. 展示 ReAct steps timeline
6. 支持 designer feedback 后 continue-run

如果切到另一个分支，建议先 stash 或 commit 当前改动。
