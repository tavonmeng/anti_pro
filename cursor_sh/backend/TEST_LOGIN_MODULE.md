# 用户登录模块测试指南

## 📋 目录

1. [准备工作](#1-准备工作)
2. [测试方式](#2-测试方式)
3. [测试用例](#3-测试用例)
4. [验证结果](#4-验证结果)
5. [常见问题](#5-常见问题)

---

## 1. 准备工作

### 1.1 确保后端服务已启动

```bash
cd backend
./run.sh
```

**成功启动的标志**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### 1.2 确认默认账户

数据库初始化后会自动创建以下测试账户：

| 角色 | 用户名 | 密码 | 说明 |
|------|--------|------|------|
| 管理员 | `admin` | `123456` | 超级管理员 |
| 负责人 | `staff1` | `123456` | 张设计 |
| 负责人 | `staff2` | `123456` | 李艺术 |

**注意**: 普通用户需要通过注册接口创建。

---

## 2. 测试方式

### 方式 1: Swagger UI（最推荐）⭐

**访问地址**: http://localhost:8000/docs

#### 步骤：

1. **打开 Swagger UI**
   ```
   http://localhost:8000/docs
   ```

2. **找到登录接口**
   - 展开 `🔐 认证` 标签
   - 找到 `POST /api/auth/login`
   - 点击接口卡片展开详情

3. **测试登录**
   - 点击 "Try it out" 按钮
   - 在请求体（Request body）中填写：
     ```json
     {
       "username": "admin",
       "password": "123456",
       "role": "admin",
       "captcha": "1234"
     }
     ```
   - 点击 "Execute" 执行请求

4. **查看响应**
   - 成功响应示例：
     ```json
     {
       "code": 200,
       "message": "登录成功",
       "data": {
         "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
         "user": {
           "id": "admin-001",
           "username": "admin",
           "role": "admin",
           "email": "admin@example.com"
         }
       }
     }
     ```

5. **设置认证 Token**
   - 复制响应中的 `token` 值
   - 点击页面右上角的 "Authorize" 🔒 按钮
   - 在弹出的对话框中输入：`Bearer <你的token>`
   - 点击 "Authorize"
   - 现在所有需要认证的接口都会自动带上 token

---

### 方式 2: 使用测试脚本（自动化测试）

**位置**: `backend/test_login.sh`

#### 使用步骤：

```bash
# 1. 进入后端目录
cd backend

# 2. 赋予执行权限（首次运行）
chmod +x test_login.sh

# 3. 运行测试脚本
./test_login.sh
```

**脚本会自动测试**:
- ✅ 管理员登录（成功）
- ✅ 用户注册
- ✅ 普通用户登录（成功）
- ✅ 错误密码（失败）
- ✅ 不存在用户（失败）
- ✅ Token 验证（访问受保护接口）

---

### 方式 3: curl 命令（命令行）

#### 测试管理员登录：

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "123456",
    "role": "admin",
    "captcha": "1234"
  }'
```

#### 格式化输出（需要安装 jq）：

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "123456",
    "role": "admin",
    "captcha": "1234"
  }' | jq .
```

#### 保存 Token 到变量：

```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "123456",
    "role": "admin",
    "captcha": "1234"
  }' | jq -r '.data.token')

echo "Token: $TOKEN"
```

#### 使用 Token 访问受保护接口：

```bash
curl -X GET "http://localhost:8000/api/orders" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

### 方式 4: Postman

1. **导入 Postman 集合**
   - 打开 Postman
   - 点击 "Import"
   - 选择文件: `api-spec/postman_collection.json`

2. **设置环境变量**
   - 创建新环境 "Development"
   - 添加变量:
     - `baseUrl`: `http://localhost:8000/api`
     - `token`: (留空，登录后自动填充)

3. **测试登录**
   - 打开 "认证 → 登录" 请求
   - 修改请求体为：
     ```json
     {
       "username": "admin",
       "password": "123456",
       "role": "admin",
       "captcha": "1234"
     }
     ```
   - 点击 "Send"
   - Token 会自动保存到环境变量

---

## 3. 测试用例

### 测试用例 1: 管理员登录（成功）

**请求**:
```json
POST /api/auth/login
{
  "username": "admin",
  "password": "123456",
  "role": "admin",
  "captcha": "1234"
}
```

**预期响应**:
- HTTP 状态码: `200`
- `code`: `200`
- `message`: `"登录成功"`
- `data.token`: JWT token 字符串
- `data.user`: 用户信息对象

---

### 测试用例 2: 普通用户注册

**请求**:
```json
POST /api/auth/register
{
  "username": "testuser",
  "email": "testuser@example.com",
  "password": "123456",
  "role": "user"
}
```

**预期响应**:
- HTTP 状态码: `200`
- `code`: `200`
- `message`: `"注册成功"`
- `data.success`: `true`

---

### 测试用例 3: 普通用户登录（成功）

**请求**:
```json
POST /api/auth/login
{
  "username": "testuser",
  "password": "123456",
  "role": "user",
  "captcha": "1234"
}
```

**预期响应**:
- HTTP 状态码: `200`
- 返回 token 和用户信息

---

### 测试用例 4: 错误密码（失败）

**请求**:
```json
POST /api/auth/login
{
  "username": "admin",
  "password": "wrongpassword",
  "role": "admin",
  "captcha": "1234"
}
```

**预期响应**:
- HTTP 状态码: `401`
- `code`: `401`
- `message`: `"用户名或密码错误"` 或 `detail`: `"用户名或密码错误"`

---

### 测试用例 5: 不存在的用户（失败）

**请求**:
```json
POST /api/auth/login
{
  "username": "nonexistent",
  "password": "123456",
  "role": "user",
  "captcha": "1234"
}
```

**预期响应**:
- HTTP 状态码: `401`
- `code`: `401`
- `message`: `"用户名或密码错误"`

---

### 测试用例 6: 角色不匹配（失败）

**请求**:
```json
POST /api/auth/login
{
  "username": "admin",
  "password": "123456",
  "role": "user",
  "captcha": "1234"
}
```

**预期响应**:
- HTTP 状态码: `401`
- 错误信息: `"用户名或密码错误"`

**说明**: 即使密码正确，如果角色不匹配，也会返回错误。

---

### 测试用例 7: 用户名已存在（注册失败）

**请求**:
```json
POST /api/auth/register
{
  "username": "admin",
  "email": "admin@example.com",
  "password": "123456",
  "role": "user"
}
```

**预期响应**:
- HTTP 状态码: `409`
- `code`: `409`
- `message`: `"用户名已存在"` 或 `detail`: `"用户名已存在"`

---

### 测试用例 8: Token 验证（访问受保护接口）

**前提**: 先登录获取 token

**请求**:
```bash
GET /api/orders
Headers:
  Authorization: Bearer <token>
```

**预期响应**:
- HTTP 状态码: `200`
- 返回订单列表（可能为空数组）

**如果 Token 无效**:
- HTTP 状态码: `401`
- `detail`: `"未提供认证信息"` 或 `"无效的认证信息"`

---

## 4. 验证结果

### 4.1 成功登录的验证点

✅ **响应状态码**: `200 OK`
✅ **响应格式**: 符合 `ApiResponse<LoginResponse>` 结构
✅ **Token 存在**: `data.token` 不为空
✅ **Token 格式**: JWT token 格式（三段式，用 `.` 分隔）
✅ **用户信息**: `data.user` 包含完整的用户信息
✅ **Token 可用**: 使用 token 可以访问受保护接口

### 4.2 失败登录的验证点

✅ **响应状态码**: `401 Unauthorized` 或 `403 Forbidden`
✅ **错误信息**: 明确提示失败原因
✅ **不返回 Token**: `data` 字段不存在或为空

### 4.3 Token 验证

**解码 Token**（可选，用于调试）:

访问 https://jwt.io/ 可以解码 JWT token，查看 payload：

```json
{
  "user_id": "admin-001",
  "username": "admin",
  "role": "admin",
  "exp": 1234567890,
  "iat": 1234567890
}
```

---

## 5. 常见问题

### Q1: 提示 "无法连接到服务器"

**原因**: 后端服务未启动

**解决**:
```bash
cd backend
./run.sh
```

---

### Q2: 登录返回 401，但密码正确

**可能原因**:
1. 角色不匹配（例如用 `user` 角色登录 `admin` 账户）
2. 用户被禁用（`is_active = False`）
3. 数据库未初始化

**解决**:
1. 检查请求中的 `role` 字段是否与账户角色匹配
2. 检查数据库中的用户状态
3. 重新运行初始化脚本: `python scripts/init_admin.py`

---

### Q3: Token 无效或过期

**原因**: 
- Token 已过期（默认 24 小时）
- Token 格式错误

**解决**:
- 重新登录获取新 token
- 检查 token 格式是否正确（Bearer 前缀）

---

### Q4: 注册时提示 "用户名已存在"

**原因**: 该用户名已被使用

**解决**: 使用其他用户名或先删除已存在的用户

---

### Q5: Swagger UI 中无法设置 Token

**解决**:
1. 点击右上角 "Authorize" 按钮
2. 输入格式: `Bearer <token>`（注意 Bearer 和 token 之间有空格）
3. 点击 "Authorize"
4. 关闭对话框后，所有请求会自动带上 token

---

## 6. 下一步测试

完成登录模块测试后，可以继续测试：

1. **订单模块**: 创建订单、查询订单、更新订单状态
2. **负责人模块**: 获取负责人列表、分配订单
3. **文件上传**: 上传订单相关文件

**相关文档**:
- 完整测试指南: `BACKEND_TESTING_GUIDE.md`
- API 规范: `api-spec/openapi.yaml`

---

## 7. 测试检查清单

- [ ] 后端服务已启动
- [ ] 数据库已初始化
- [ ] 管理员账户可以登录
- [ ] 可以注册新用户
- [ ] 新用户可以使用注册的账户登录
- [ ] 错误密码返回 401
- [ ] 不存在用户返回 401
- [ ] 角色不匹配返回 401
- [ ] Token 可以用于访问受保护接口
- [ ] Token 过期后无法访问受保护接口

---

**测试完成后，请记录测试结果和发现的问题！** 🎉

