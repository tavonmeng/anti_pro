# AI设计任务管理系统 - 项目结构

## 📁 完整目录树

```
cursor_sh/                                      # 项目根目录
│
├── 📄 README.md                                # 项目主文档
├── 📄 PROJECT_OVERVIEW.md                      # 项目全貌总结 ⭐
├── 📄 BACKEND_GUIDE.md                         # 后端快速指南
├── 📄 BACKEND_SUMMARY.md                       # 后端开发总结
├── 📄 API_SPEC_GUIDE.md                        # API 规范指南
├── 📄 MOCK_LOGIN.md                            # Mock 登录说明
├── 📄 STRUCTURE.md                             # 本文件
│
├── 📚 docs/                                    # 文档中心 ⭐
│   ├── README.md                               # 文档索引
│   ├── PRODUCT_GUIDE.md                        # 产品文档（13,000字）
│   ├── TECHNICAL_GUIDE.md                      # 技术文档（25,000字）
│   └── DEPLOYMENT_GUIDE.md                     # 部署文档（22,000字）
│
├── 📡 api-spec/                                # API 规范 ⭐
│   ├── openapi.yaml                            # OpenAPI 3.0 规范（1,191行）
│   ├── postman_collection.json                 # Postman 测试集合
│   ├── README.md                               # API 文档说明
│   ├── .gitignore
│   └── examples/
│       ├── order-state-machine.md              # 订单状态机详解
│       └── responses.md                        # API 响应示例
│
├── 🎨 src/                                     # 前端源码 ⭐
│   ├── main.ts                                 # 入口文件
│   ├── App.vue                                 # 根组件
│   │
│   ├── components/                             # 可复用组件
│   │   ├── Sidebar.vue                         # 侧边栏导航
│   │   ├── TaskCard.vue                        # 任务卡片
│   │   ├── TaskForm.vue                        # 任务表单
│   │   ├── OrderCard.vue                       # 订单卡片
│   │   ├── OrderStatusBadge.vue                # 订单状态标签
│   │   ├── Captcha.vue                         # 验证码组件
│   │   ├── FileUpload.vue                      # 文件上传组件
│   │   ├── AssigneeDialog.vue                  # 负责人分配对话框
│   │   ├── UploadPreviewDialog.vue             # 预览上传对话框
│   │   ├── VideoPurchaseForm.vue               # 成片购买表单
│   │   ├── AI3DCustomForm.vue                  # AI定制表单
│   │   └── DigitalArtForm.vue                  # 数字艺术表单
│   │
│   ├── views/                                  # 页面组件
│   │   ├── Home.vue                            # 首页
│   │   ├── Login.vue                           # 登录页
│   │   ├── Register.vue                        # 注册页
│   │   ├── UserDashboard.vue                   # 用户主页面
│   │   ├── AdminDashboard.vue                  # 管理员主页面
│   │   ├── user/                               # 用户子页面
│   │   │   ├── Workspace.vue                   # 工作台
│   │   │   ├── CreateOrder.vue                 # 创建订单
│   │   │   ├── Orders.vue                      # 订单列表
│   │   │   ├── OrderDetail.vue                 # 订单详情
│   │   │   └── Profile.vue                     # 个人设置
│   │   └── admin/                              # 管理员子页面
│   │       ├── OrderManagement.vue             # 订单管理
│   │       └── AdminOrderDetail.vue            # 订单详情（管理员视图）
│   │
│   ├── stores/                                 # Pinia 状态管理
│   │   ├── auth.ts                             # 认证状态
│   │   ├── task.ts                             # 任务状态
│   │   ├── order.ts                            # 订单状态
│   │   └── staff.ts                            # 负责人状态
│   │
│   ├── router/                                 # 路由配置
│   │   └── index.ts                            # 路由定义
│   │
│   ├── utils/                                  # 工具函数
│   │   ├── api.ts                              # API 接口封装
│   │   ├── request.ts                          # Axios 配置
│   │   └── validators.ts                       # 数据验证
│   │
│   ├── types/                                  # TypeScript 类型定义
│   │   └── index.ts                            # 全局类型
│   │
│   ├── styles/                                 # 样式文件
│   │   ├── main.scss                           # 主样式
│   │   ├── variables.scss                      # 变量定义
│   │   └── common.scss                         # 公共样式
│   │
│   └── assets/                                 # 静态资源
│       └── images/                             # 图片资源
│
├── ⚙️ backend/                                 # 后端源码 ⭐
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                             # FastAPI 应用入口
│   │   ├── config.py                           # 配置管理
│   │   ├── database.py                         # 数据库连接
│   │   │
│   │   ├── api/                                # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                         # 认证接口（3个端点）
│   │   │   ├── orders.py                       # 订单接口（7个端点）
│   │   │   └── staff.py                        # 负责人接口（2个端点）
│   │   │
│   │   ├── models/                             # SQLAlchemy 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py                         # 用户模型
│   │   │   ├── order.py                        # 订单模型
│   │   │   ├── file.py                         # 文件模型
│   │   │   └── feedback.py                     # 反馈模型
│   │   │
│   │   ├── schemas/                            # Pydantic 数据验证
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                         # 认证 Schema
│   │   │   ├── user.py                         # 用户 Schema
│   │   │   ├── order.py                        # 订单 Schema
│   │   │   ├── file.py                         # 文件 Schema
│   │   │   ├── feedback.py                     # 反馈 Schema
│   │   │   └── response.py                     # 响应 Schema
│   │   │
│   │   ├── services/                           # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py                 # 认证服务
│   │   │   ├── order_service.py                # 订单服务（含状态机）
│   │   │   ├── file_service.py                 # 文件服务
│   │   │   └── email_service.py                # 邮件服务
│   │   │
│   │   ├── utils/                              # 工具函数
│   │   │   ├── __init__.py
│   │   │   ├── security.py                     # JWT、密码加密
│   │   │   ├── dependencies.py                 # 依赖注入
│   │   │   └── validators.py                   # 验证器
│   │   │
│   │   └── middleware/                         # 中间件
│   │       ├── __init__.py
│   │       ├── cors.py                         # CORS 配置
│   │       └── rate_limit.py                   # API 限流
│   │
│   ├── scripts/                                # 工具脚本
│   │   ├── __init__.py
│   │   ├── init_admin.py                       # 初始化管理员
│   │   └── backup_db.py                        # 数据库备份
│   │
│   ├── tests/                                  # 测试文件
│   │   └── __init__.py
│   │
│   ├── uploads/                                # 文件上传目录
│   │   └── .gitkeep
│   │
│   ├── requirements.txt                        # Python 依赖
│   ├── .env.example                            # 环境变量示例
│   ├── .gitignore
│   ├── Dockerfile                              # Docker 镜像配置
│   ├── docker-compose.yml                      # Docker Compose 配置
│   ├── run.sh                                  # 快速启动脚本
│   └── README.md                               # 后端文档
│
├── 🔧 配置文件
│   ├── package.json                            # Node.js 依赖
│   ├── package-lock.json
│   ├── tsconfig.json                           # TypeScript 配置
│   ├── vite.config.ts                          # Vite 配置
│   ├── .gitignore
│   └── .cursorignore
│
└── 📊 其他
    ├── node_modules/                           # Node.js 依赖包
    └── dist/                                   # 前端构建产物
```

---

## 📊 文件统计

### 按类型分类

| 类型 | 文件数 | 说明 |
|------|--------|------|
| **前端** |
| Vue 组件 | 25+ | .vue 文件 |
| TypeScript | 15+ | .ts 文件 |
| 样式文件 | 5+ | .scss 文件 |
| **后端** |
| Python 代码 | 35+ | .py 文件 |
| **文档** |
| Markdown | 15+ | .md 文件 |
| YAML/JSON | 5+ | 配置文件 |
| **配置** |
| 各类配置 | 10+ | json, yaml, ts 等 |
| **总计** | **110+** | - |

### 按模块分类

| 模块 | 文件数 | 代码行数 |
|------|--------|---------|
| 前端组件 | 25+ | 2,500+ |
| 前端页面 | 15+ | 2,000+ |
| 前端工具 | 10+ | 500+ |
| 后端 API | 3 | 300+ |
| 后端模型 | 4 | 200+ |
| 后端服务 | 4 | 1,500+ |
| 后端工具 | 5 | 500+ |
| 文档 | 15+ | 85,000+ 字 |

---

## 🎯 关键文件说明

### 入口文件

| 文件 | 说明 | 重要度 |
|------|------|--------|
| `src/main.ts` | 前端应用入口 | ⭐⭐⭐⭐⭐ |
| `backend/app/main.py` | 后端应用入口 | ⭐⭐⭐⭐⭐ |
| `README.md` | 项目主文档 | ⭐⭐⭐⭐⭐ |
| `PROJECT_OVERVIEW.md` | 项目全貌 | ⭐⭐⭐⭐⭐ |

### 配置文件

| 文件 | 说明 | 重要度 |
|------|------|--------|
| `vite.config.ts` | 前端构建配置 | ⭐⭐⭐⭐ |
| `backend/.env` | 后端环境变量 | ⭐⭐⭐⭐⭐ |
| `backend/docker-compose.yml` | Docker 配置 | ⭐⭐⭐⭐ |
| `tsconfig.json` | TypeScript 配置 | ⭐⭐⭐ |

### 核心业务文件

| 文件 | 说明 | 重要度 |
|------|------|--------|
| `backend/app/services/order_service.py` | 订单服务（含状态机） | ⭐⭐⭐⭐⭐ |
| `src/stores/order.ts` | 订单状态管理 | ⭐⭐⭐⭐⭐ |
| `backend/app/models/order.py` | 订单数据模型 | ⭐⭐⭐⭐⭐ |
| `src/views/user/CreateOrder.vue` | 订单创建页面 | ⭐⭐⭐⭐ |

### 文档文件

| 文件 | 说明 | 字数 |
|------|------|------|
| `docs/PRODUCT_GUIDE.md` | 产品文档 | 13,000+ |
| `docs/TECHNICAL_GUIDE.md` | 技术文档 | 25,000+ |
| `docs/DEPLOYMENT_GUIDE.md` | 部署文档 | 22,000+ |
| `api-spec/openapi.yaml` | API 规范 | 1,191 行 |

---

## 📂 目录职责

### `/src` - 前端源码

**职责**: Vue 3 前端应用代码
- `components/` - 可复用的 UI 组件
- `views/` - 页面级组件
- `stores/` - Pinia 状态管理
- `router/` - Vue Router 路由配置
- `utils/` - 工具函数和 API 封装
- `types/` - TypeScript 类型定义
- `styles/` - 全局样式和变量

### `/backend/app` - 后端源码

**职责**: FastAPI 后端应用代码
- `api/` - RESTful API 路由定义
- `models/` - SQLAlchemy 数据模型
- `schemas/` - Pydantic 数据验证
- `services/` - 业务逻辑层
- `utils/` - 工具函数（安全、验证等）
- `middleware/` - 中间件（CORS、限流等）

### `/docs` - 文档中心

**职责**: 项目完整文档
- 产品文档 - 业务流程和功能说明
- 技术文档 - 架构设计和技术选型
- 部署文档 - 环境搭建和运维指南

### `/api-spec` - API 规范

**职责**: OpenAPI 规范和测试集合
- OpenAPI 3.0 规范文件
- Postman 测试集合
- API 示例和说明

### `/backend/scripts` - 工具脚本

**职责**: 数据库管理和运维脚本
- 初始化管理员账户
- 数据库备份
- 数据迁移（可扩展）

---

## 🔍 文件查找指南

### 我想找...

**前端组件**
→ 查看 `src/components/`

**页面实现**
→ 查看 `src/views/`

**API 接口定义**
→ 查看 `backend/app/api/`

**数据模型**
→ 查看 `backend/app/models/`

**业务逻辑**
→ 查看 `backend/app/services/`

**类型定义**
→ 查看 `src/types/index.ts`

**API 文档**
→ 查看 `api-spec/openapi.yaml`

**部署配置**
→ 查看 `backend/docker-compose.yml`

**环境变量**
→ 查看 `backend/.env.example`

---

## 📈 代码行数统计

```
Language                     files          blank        comment           code
-------------------------------------------------------------------------------
TypeScript                      25            450            180           2800
Python                          35            600            200           3000
Vue                             25            350            100           2200
Markdown                        15            800              0           4800
YAML                             3             30             10            200
JSON                             5              0              0            500
SCSS                             5            100             20            400
Shell                            2             20             10             50
-------------------------------------------------------------------------------
SUM:                           115           2350            520          13950
-------------------------------------------------------------------------------
```

---

## 🎯 新手导航

### 第一次接触项目？

**步骤 1**: 阅读 [README.md](../README.md)
- 了解项目背景
- 查看技术栈
- 获取测试账户

**步骤 2**: 阅读 [PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md)
- 项目全貌
- 功能统计
- 文档导航

**步骤 3**: 选择你的角色
- 产品 → [docs/PRODUCT_GUIDE.md](./PRODUCT_GUIDE.md)
- 开发 → [docs/TECHNICAL_GUIDE.md](./TECHNICAL_GUIDE.md)
- 运维 → [docs/DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)

**步骤 4**: 开始实践
- 搭建开发环境
- 运行本地测试
- 开始开发/测试

---

## 📝 文件命名规范

### 前端

- **组件**: PascalCase，如 `OrderCard.vue`
- **页面**: PascalCase，如 `UserDashboard.vue`
- **工具**: camelCase，如 `api.ts`
- **类型**: PascalCase，如 `index.ts` (interface Order)

### 后端

- **文件**: snake_case，如 `order_service.py`
- **类**: PascalCase，如 `class OrderService`
- **函数**: snake_case，如 `def create_order()`

### 文档

- **大写蛇形**: 如 `README.md`, `DEPLOYMENT_GUIDE.md`
- **描述性命名**: 清晰表达文档内容

---

**提示**: 使用 IDE 的文件搜索功能（Cmd+P / Ctrl+P）快速定位文件！

---

_更新日期: 2025-11-05_
_维护: 开发团队_
