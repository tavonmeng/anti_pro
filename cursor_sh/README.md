# 任务管理系统

基于 Vue 3 + TypeScript 的现代化任务管理系统，支持管理员和普通用户两种角色。

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - 类型安全的 JavaScript 超集
- **Vite** - 下一代前端构建工具
- **Element Plus** - Vue 3 组件库
- **Pinia** - Vue 的状态管理库
- **Vue Router** - Vue.js 官方路由管理器
- **Axios** - 基于 Promise 的 HTTP 客户端
- **SCSS** - CSS 预处理器

## 功能特性

### 用户功能
- ✅ 任务提交（支持文字描述和图片上传）
- ✅ 任务管理（查看、修改、删除自己的任务）
- ✅ 状态跟踪（实时查看任务处理进度）
- ✅ 任务筛选（按状态筛选任务）

### 管理员功能
- ✅ 任务总览（查看所有用户提交的任务）
- ✅ 状态管理（修改任务进展状态）
- ✅ 数据统计（任务数量统计面板）
- ✅ 任务管理（支持筛选、排序、删除）

## 项目结构

```
src/
├── components/     # 可复用组件
│   ├── Sidebar.vue      # 侧边导航栏
│   ├── TaskCard.vue     # 任务卡片
│   └── TaskForm.vue     # 任务表单
├── views/         # 页面组件
│   ├── Login.vue        # 登录页面
│   ├── UserDashboard.vue    # 用户主界面
│   └── AdminDashboard.vue   # 管理员主界面
├── stores/        # 状态管理
│   ├── auth.ts          # 认证状态
│   └── task.ts          # 任务状态
├── router/        # 路由配置
│   └── index.ts
├── utils/         # 工具函数
│   ├── request.ts       # Axios 配置
│   └── api.ts          # API 接口
├── styles/        # 样式文件
│   ├── main.scss        # 全局样式
│   └── variables.scss   # 样式变量
├── types/         # TypeScript类型定义
│   └── index.ts
├── App.vue        # 根组件
└── main.ts        # 入口文件
```

## 安装依赖

```bash
npm install
```

## 开发运行

```bash
npm run dev
```

## 模拟登录测试

系统已启用模拟登录功能，可以使用以下测试账号：

### 普通用户
- **用户名**: `user`
- **密码**: `123456`
- **角色**: 选择"普通用户"

### 管理员
- **用户名**: `admin`
- **密码**: `123456`
- **角色**: 选择"管理员"

详细说明请查看 [MOCK_LOGIN.md](./MOCK_LOGIN.md)

## 📚 完整文档

为了方便开发和维护，我们提供了完整的文档体系：

### 核心文档
- 📖 [项目总览](./PROJECT_OVERVIEW.md) - 项目全貌和功能统计
- 🏗️ [代码结构指南](./docs/CODE_STRUCTURE.md) - **代码组织和开发指南** ⭐
- 📁 [文件结构](./STRUCTURE.md) - 项目文件目录说明

### 专项文档
- 👥 [产品文档](./docs/PRODUCT_GUIDE.md) - 业务流程和功能说明（13,000字）
- 🔧 [技术文档](./docs/TECHNICAL_GUIDE.md) - 架构设计和技术选型（25,000字）
- 🚀 [部署文档](./docs/DEPLOYMENT_GUIDE.md) - 环境搭建和运维指南（22,000字）

### API 文档
- 📡 [API 规范](./api-spec/README.md) - OpenAPI 3.0 接口规范
- 📮 [Postman 集合](./api-spec/postman_collection.json) - API 测试集合

### 后端文档
- ⚙️ [后端指南](./BACKEND_GUIDE.md) - FastAPI 后端快速开始
- 📝 [后端总结](./BACKEND_SUMMARY.md) - 后端开发完成总结
- 🔌 [前后端联调](./INTEGRATION_GUIDE.md) - 联调测试指南

> **💡 开发提示**: 
> - 首次接触项目？先看 [项目总览](./PROJECT_OVERVIEW.md)
> - 要修改代码功能？查看 [代码结构指南](./docs/CODE_STRUCTURE.md)
> - 需要部署上线？参考 [部署文档](./docs/DEPLOYMENT_GUIDE.md)

## 构建生产

```bash
npm run build
```

## 预览生产构建

```bash
npm run preview
```

## API 接口规范

系统已生成完整的 **OpenAPI 3.0 规范文档**，详细说明所有后端 API 接口。

📁 **API 文档位置**: `api-spec/`

### 快速开始

1. **查看在线文档**（推荐）
   ```bash
   # 安装 swagger-ui-watcher
   npm install -g swagger-ui-watcher
   
   # 启动文档服务器
   swagger-ui-watcher api-spec/openapi.yaml
   ```
   然后访问 `http://localhost:8000`

2. **导入 Postman**
   - 打开 Postman
   - 导入 `api-spec/postman_collection.json`
   - 开始测试 API

3. **查看文档**
   - `api-spec/README.md` - API 文档总览
   - `api-spec/openapi.yaml` - OpenAPI 规范文件
   - `api-spec/examples/` - 示例和详细说明

### 主要 API 模块

#### 认证模块
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/logout` - 用户登出

#### 订单模块
- `GET /api/orders` - 获取订单列表
- `POST /api/orders` - 创建订单
- `GET /api/orders/{orderId}` - 获取订单详情
- `PUT /api/orders/{orderId}/status` - 更新订单状态
- `PUT /api/orders/{orderId}/assign` - 分配负责人
- `POST /api/orders/{orderId}/preview` - 上传预览文件
- `POST /api/orders/{orderId}/feedback` - 提交反馈

#### 负责人模块
- `GET /api/staff` - 获取负责人列表
- `POST /api/staff` - 添加负责人

详细接口说明请查看 [API 规范文档](./api-spec/README.md)

## 设计风格

- **视觉风格**: 参照苹果官网的简洁、现代设计
- **配色方案**: 浅色主题，使用中性色调
- **字体选择**: San Francisco 字体族
- **布局方案**: Flexbox/Grid 响应式布局

## 开发规范

- 使用 TypeScript 增强类型安全
- 组件化开发，提高代码复用性
- 响应式设计，支持多设备访问
- 代码注释完整，便于维护

## 浏览器支持

现代浏览器和最新版本的 Chrome、Firefox、Safari、Edge。

## 许可证

MIT

