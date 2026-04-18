# 前后端联调问题修复说明

## 修复时间
2025-11-06

## 问题描述

1. **API路径不匹配**
   - 前端请求：`/api/login`、`/api/register`
   - 后端路由：`/api/auth/login`、`/api/auth/register`
   - 导致前端无法正确调用后端接口

2. **模拟模式掩盖问题**
   - `ENABLE_MOCK = true` 导致API失败时使用模拟数据
   - 注册的用户只保存在 localStorage，未写入数据库
   - 登录时使用模拟数据，无法验证真实数据库中的用户

3. **Vite代理配置缺失**
   - 前端直接请求 `/api` 无法正确转发到后端

4. **错误信息显示不完整**
   - 401错误时显示通用提示，未显示后端返回的具体错误信息

## 修复内容

### 1. 修复前端 API 路径

**文件**: `src/utils/api.ts`

- ✅ 将 `/login` 改为 `/auth/login`
- ✅ 将 `/register` 改为 `/auth/register`
- ✅ 将 `/logout` 改为 `/auth/logout`

### 2. 配置 Vite 开发代理

**文件**: `vite.config.ts`

添加了代理配置：
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    secure: false
  }
}
```

### 3. 关闭模拟模式

**文件**: `src/utils/api.ts`

- ✅ 将 `ENABLE_MOCK` 从 `true` 改为 `false`
- ✅ 现在所有请求都使用真实后端API

### 4. 改进错误处理

**文件**: `src/utils/request.ts`

- ✅ 优先显示后端返回的 `detail` 或 `message` 字段
- ✅ 登录页面的401错误不跳转，只显示错误信息
- ✅ 添加了409冲突错误的处理
- ✅ 改进了网络连接失败的提示信息

## 测试步骤

### 1. 重启前端开发服务器

```bash
# 停止当前的前端服务（Ctrl+C）
# 重新启动
npm run dev
```

**重要**: 修改 `vite.config.ts` 后必须重启前端服务才能生效！

### 2. 确保后端服务运行

```bash
cd backend
./run.sh
```

确保后端服务在 `http://localhost:8000` 运行。

### 3. 测试用户注册

1. 打开前端页面：`http://localhost:3000/register`
2. 填写注册信息：
   - 用户名：`testuser001`
   - 邮箱：`testuser001@example.com`
   - 密码：`123456`
   - 确认密码：`123456`
   - 验证码：输入验证码
3. 点击"注册"
4. **验证**：
   - ✅ 应该显示"注册成功"提示
   - ✅ 应该跳转到登录页面
   - ✅ 在数据库中应该能找到新注册的用户

**检查数据库**:
```bash
cd backend
sqlite3 app.db "SELECT id, username, email, role, created_at FROM users WHERE username = 'testuser001';"
```

### 4. 测试用户登录

1. 打开前端页面：`http://localhost:3000/login`
2. 使用刚注册的账户登录：
   - 用户名：`testuser001`
   - 密码：`123456`
   - 验证码：输入验证码
3. 点击"登录"
4. **验证**：
   - ✅ 应该显示"登录成功"提示
   - ✅ 应该跳转到用户工作台
   - ✅ Token 应该保存到 localStorage

### 5. 测试错误情况

#### 5.1 错误密码
- 使用错误的密码登录
- ✅ 应该显示"用户名或密码错误"（后端返回的具体错误信息）

#### 5.2 不存在用户
- 使用不存在的用户名登录
- ✅ 应该显示"用户名或密码错误"

#### 5.3 重复用户名注册
- 尝试注册已存在的用户名
- ✅ 应该显示"用户名已存在"（409错误）

## 验证清单

- [ ] 前端服务已重启（修改 vite.config.ts 后必须重启）
- [ ] 后端服务正在运行（http://localhost:8000）
- [ ] 可以成功注册新用户
- [ ] 注册的用户已保存到数据库
- [ ] 可以使用注册的账户登录
- [ ] 错误信息正确显示（不是通用提示）
- [ ] 登录后可以正常访问用户工作台

## 常见问题

### Q1: 前端请求仍然失败，显示网络错误

**原因**: 
- 后端服务未启动
- Vite 代理配置未生效（需要重启前端服务）

**解决**:
1. 确认后端服务运行：`curl http://localhost:8000/health`
2. 重启前端服务：停止后重新运行 `npm run dev`

### Q2: 注册成功但数据库中没有用户

**原因**: 
- 模拟模式可能仍然开启
- 后端注册接口出错

**解决**:
1. 检查 `src/utils/api.ts` 中 `ENABLE_MOCK` 是否为 `false`
2. 查看浏览器控制台和网络请求，确认请求是否发送到 `/api/auth/register`
3. 查看后端日志，确认是否有错误信息

### Q3: 登录时显示"用户名或密码错误"，但密码正确

**原因**: 
- 角色不匹配（例如用 `user` 角色登录 `admin` 账户）
- 用户被禁用

**解决**:
1. 确认登录时选择的角色与数据库中的角色一致
2. 检查数据库中用户的 `is_active` 字段是否为 `1`

### Q4: 401错误时仍然跳转到登录页

**原因**: 
- 错误处理逻辑判断路径不正确

**解决**:
- 检查 `src/utils/request.ts` 中的路径判断逻辑
- 确认当前路径是否为 `/login` 或 `/admin/login`

## 技术细节

### API路径映射

| 前端调用 | 实际请求 | 后端路由 |
|---------|---------|---------|
| `request.post('/auth/login')` | `http://localhost:3000/api/auth/login` | `POST /api/auth/login` |
| `request.post('/auth/register')` | `http://localhost:3000/api/auth/register` | `POST /api/auth/register` |
| `request.post('/auth/logout')` | `http://localhost:3000/api/auth/logout` | `POST /api/auth/logout` |

### Vite代理工作原理

1. 前端请求：`/api/auth/login`
2. Vite代理拦截：匹配 `/api` 前缀
3. 转发到后端：`http://localhost:8000/api/auth/login`
4. 后端处理请求并返回响应
5. Vite代理将响应返回给前端

### 响应格式

**成功响应**:
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGci...",
    "user": { ... }
  }
}
```

**错误响应**:
```json
{
  "detail": "用户名或密码错误"
}
```

前端响应拦截器会：
1. 提取 `response.data.data`（成功时）
2. 提取 `error.response.data.detail`（错误时）

## 下一步

修复完成后，可以继续测试：
1. 订单模块的前后端联调
2. 负责人管理模块的前后端联调
3. 文件上传功能的前后端联调

---

**修复完成时间**: 2025-11-06  
**修复人员**: AI Assistant

