# 注册功能调试指南

## 问题描述
注册新用户时页面返回"请求失败"

## 已修复的问题
✅ **注册接口返回值处理** - 已修复 `authApi.register` 函数，正确提取 `success` 字段

## 调试步骤

### 1. 检查后端服务是否运行

```bash
# 检查后端服务
curl http://localhost:8000/health

# 应该返回: {"status":"ok","app":"AI设计任务管理系统"}
```

如果无法连接，启动后端服务：
```bash
cd backend
./run.sh
```

### 2. 检查前端服务是否运行

```bash
# 检查前端服务
curl http://localhost:3000

# 应该返回 HTML 页面
```

如果无法连接，启动前端服务：
```bash
npm run dev
```

### 3. 检查浏览器控制台

打开浏览器开发者工具（F12），查看：
- **Console 标签**：查看是否有 JavaScript 错误
- **Network 标签**：查看注册请求的详细信息

**关键检查点**：
1. 请求 URL 是否为：`http://localhost:3000/api/auth/register`
2. 请求方法是否为：`POST`
3. 请求状态码是什么：
   - `200` - 成功
   - `404` - 路径错误
   - `500` - 服务器错误
   - `CORS error` - CORS 配置问题
   - `Network Error` - 网络连接问题

### 4. 检查请求格式

在浏览器 Network 标签中，点击注册请求，查看：

**Request Headers**:
```
Content-Type: application/json
```

**Request Payload**:
```json
{
  "username": "testuser",
  "email": "testuser@example.com",
  "password": "123456",
  "role": "user"
}
```

### 5. 检查响应格式

**成功响应** (HTTP 200):
```json
{
  "code": 200,
  "message": "注册成功",
  "data": {
    "success": true
  }
}
```

**错误响应** (HTTP 409):
```json
{
  "detail": "用户名已存在"
}
```

### 6. 常见问题排查

#### 问题 1: 404 Not Found

**原因**: API 路径错误或后端路由未注册

**检查**:
```bash
# 测试后端接口
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"test123","email":"test123@test.com","password":"123456","role":"user"}'
```

**解决**:
- 确认后端 `app/main.py` 中已注册 `auth.router`
- 确认前端请求路径为 `/auth/register`

#### 问题 2: CORS 错误

**原因**: 后端 CORS 配置不允许前端源

**检查**:
- 查看浏览器控制台的 CORS 错误信息
- 检查后端 `app/config.py` 中的 `CORS_ORIGINS` 配置

**解决**:
```python
# backend/app/config.py
CORS_ORIGINS: Union[List[str], str] = [
    "http://localhost:5173",  # Vite 默认端口
    "http://localhost:3000"   # 你的前端端口
]
```

#### 问题 3: Network Error

**原因**: 
- 后端服务未启动
- Vite 代理配置未生效
- 端口冲突

**检查**:
```bash
# 检查端口占用
lsof -ti:8000  # 后端端口
lsof -ti:3000  # 前端端口
```

**解决**:
1. 确认后端服务运行在 `http://localhost:8000`
2. 重启前端服务（修改 vite.config.ts 后必须重启）
3. 检查 `vite.config.ts` 中的代理配置

#### 问题 4: 请求格式错误

**原因**: 前端发送的数据格式不符合后端要求

**检查**:
- 查看浏览器 Network 标签中的 Request Payload
- 确认字段名：`username`, `email`, `password`, `role`

**解决**:
- 确认前端发送的数据格式正确
- 检查 `Register.vue` 中的表单数据

#### 问题 5: 验证码问题

**原因**: 验证码验证失败

**检查**:
- 查看浏览器控制台是否有验证码相关错误
- 确认验证码组件正常工作

**解决**:
- 确保验证码已通过验证
- 检查 `captchaValid.value` 是否为 `true`

### 7. 手动测试后端接口

```bash
# 测试注册接口
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser001",
    "email": "testuser001@example.com",
    "password": "123456",
    "role": "user"
  }'

# 成功响应示例:
# {"code":200,"message":"注册成功","data":{"success":true}}
```

### 8. 检查数据库

```bash
cd backend
sqlite3 app.db "SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC LIMIT 5;"
```

### 9. 查看后端日志

查看后端服务的控制台输出，确认：
- 是否有错误信息
- 请求是否到达后端
- 数据库操作是否成功

## 快速修复检查清单

- [ ] 后端服务正在运行（`http://localhost:8000`）
- [ ] 前端服务已重启（修改配置后必须重启）
- [ ] Vite 代理配置正确（`vite.config.ts`）
- [ ] CORS 配置包含前端地址（`backend/app/config.py`）
- [ ] 浏览器控制台无 JavaScript 错误
- [ ] Network 标签显示请求已发送
- [ ] 请求路径正确（`/api/auth/register`）
- [ ] 请求格式正确（JSON，包含所有必需字段）
- [ ] 验证码已通过验证

## 如果问题仍然存在

请提供以下信息：
1. 浏览器控制台的完整错误信息（Console 和 Network 标签）
2. 后端服务的日志输出
3. 网络请求的详细信息（URL、方法、状态码、请求体、响应体）

---

**修复时间**: 2025-11-06

