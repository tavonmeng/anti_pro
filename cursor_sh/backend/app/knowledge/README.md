# AI Agent 知识库

本目录存放 AI Agent 对话时引用的所有业务知识文件。
运营或产品团队可以随时修改这些文件，**无需修改代码**，重启后端服务即可生效。

## 文件说明

| 文件 | 用途 | 修改频率 |
|------|------|----------|
| `business_intro.md` | 公司业务介绍（三大业务板块、价格参考等） | 低 — 核心业务变动时 |
| `cases.json` | 案例库（结构化数据，前端卡片渲染用） | 中 — 新增/更新案例时 |
| `cases.md` | 案例库（文本版，供 LLM 理解上下文用） | 中 — 与 cases.json 同步更新 |

## 使用方式

- AI 业务介绍 Agent 会自动读取 `business_intro.md` + `cases.json` 作为 LLM 的知识上下文
- AI 案例数据接口 `/ai/cases` 直接返回 `cases.json` 的内容

## 修改指南

### business_intro.md
纯文本 Markdown，用中文书写即可。格式参考现有内容。

### cases.json
JSON 数组格式，每个案例包含以下字段：
```json
{
  "id": "case_004",          // 唯一标识，格式 case_XXX
  "title": "案例名称",
  "category": "ai_3d_custom", // ai_3d_custom / video_purchase / digital_art
  "description": "案例描述",
  "channel": "投放渠道",
  "highlights": "项目亮点",
  "duration": "制作周期",
  "video_url": "/static/cases/case_004.mp4",
  "thumbnail_url": "/static/cases/case_004_thumb.jpg"
}
```

### cases.md
`cases.json` 的文本版，供 LLM 在对话中引用。与 `cases.json` 内容保持一致即可。
