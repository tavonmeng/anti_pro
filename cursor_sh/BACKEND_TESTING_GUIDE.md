# 后端测试与联调完整指南

## 📋 目录

1. [后端环境准备](#1-后端环境准备)
2. [后端启动](#2-后端启动)
3. [后端独立测试](#3-后端独立测试)
4. [前后端联调](#4-前后端联调)
5. [常见问题](#5-常见问题)

---

## 1. 后端环境准备

### 环境要求

- **Python**: 3.11 或更高版本
- **pip**: Python 包管理器
- **操作系统**: macOS / Linux / Windows

### 检查环境

```bash
# 检查 Python 版本
python3 --version
# 应显示: Python 3.11.x 或更高

# 检查 pip
pip3 --version
```

---

## 2. 后端启动

### 方式 1: 使用快速启动脚本（推荐）⭐

这是**最简单**的方式，脚本会自动完成所有设置：

```bash
# 1. 进入后端目录
cd backend

# 2. 赋予脚本执行权限（首次运行）
chmod +x run.sh

# 3. 运行启动脚本
./run.sh
```

**脚本会自动完成**:
- ✅ 创建虚拟环境 (`venv/`)
- ✅ 安装所有依赖包
- ✅ 复制环境变量文件 (`.env`)
- ✅ 初始化数据库 (`app.db`)
- ✅ 创建默认管理员账户
- ✅ 启动开发服务器

**启动成功后会显示**:
```
🎉 准备工作完成！

启动服务器...
API 文档: http://localhost:8000/docs

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

### 方式 2: 手动启动（了解每一步）

如果你想了解每一步的细节，可以手动执行：

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境
python3 -m venv venv

# 3. 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或在 Windows: venv\Scripts\activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置环境变量
cp .env.example .env
# 可选：编辑 .env 文件配置邮件等参数
# nano .env

# 6. 初始化数据库和管理员账户
python scripts/init_admin.py

# 7. 启动服务器
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**参数说明**:
- `--reload`: 代码修改后自动重启（开发模式）
- `--host 0.0.0.0`: 允许外部访问
- `--port 8000`: 监听 8000 端口

---

### 默认账户信息

数据库初始化后会自动创建：

| 角色 | 用户名 | 密码 | 说明 |
|------|--------|------|------|
| 管理员 | `admin` | `123456` | 超级管理员 |
| 负责人 | `staff1` | `123456` | 张设计 |
| 负责人 | `staff2` | `123456` | 李艺术 |

**注意**: 普通用户需要通过注册接口或前端注册页面创建。

---

## 3. 后端独立测试

后端启动后，有 **4 种方式** 独立测试 API：

### 方式 1: Swagger UI（最推荐）⭐

这是最直观、最方便的测试方式！

**访问地址**: http://localhost:8000/docs

**特点**:
- ✅ 可视化界面
- ✅ 自动生成的 API 文档
- ✅ 在线测试所有接口
- ✅ 自动生成请求示例
- ✅ 查看响应格式

**使用步骤**:

1. **打开 Swagger UI**
   ```
   http://localhost:8000/docs
   ```

2. **测试登录接口**
   - 找到 `POST /api/auth/login`
   - 点击 "Try it out"
   - 填写请求体:
     ```json
     {
       "username": "admin",
       "password": "123456",
       "role": "admin",
       "captcha": "1234"
     }
     ```
   - 点击 "Execute"
   - 复制响应中的 `token`

3. **设置认证**
   - 点击页面右上角的 "Authorize" 按钮
   - 输入: `Bearer <你的token>`
   - 点击 "Authorize"
   - 现在所有需要认证的接口都会自动带上 token

4. **测试其他接口**
   - 例如获取订单列表: `GET /api/orders`
   - 创建订单: `POST /api/orders`
   - 更新订单状态: `PUT /api/orders/{orderId}/status`

**Swagger UI 截图说明**:
```
┌─────────────────────────────────────────┐
│  AI设计任务管理系统 API     [Authorize] │
├─────────────────────────────────────────┤
│  🔐 认证                                │
│    POST /api/auth/login                 │
│    POST /api/auth/register              │
│    POST /api/auth/logout                │
│                                         │
│  📦 订单                                │
│    GET  /api/orders                     │
│    POST /api/orders                     │
│    GET  /api/orders/{orderId}           │
│    PUT  /api/orders/{orderId}/status    │
│    ...                                  │
│                                         │
│  👥 负责人                              │
│    GET  /api/staff                      │
│    POST /api/staff                      │
│    ...                                  │
└─────────────────────────────────────────┘
```

---

### 方式 2: curl 命令（命令行）

适合快速测试和脚本自动化。

**测试登录**:
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

**响应示例**:
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "admin-001",
      "username": "admin",
      "role": "admin"
    }
  }
}
```

**保存 Token 到变量**:
```bash
# 登录并提取 token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "123456",
    "role": "admin"
  }' | jq -r '.data.token')

echo "Token: $TOKEN"
```

**使用 Token 访问受保护的接口**:
```bash
# 获取订单列表
curl -X GET "http://localhost:8000/api/orders" \
  -H "Authorization: Bearer $TOKEN"

# 获取负责人列表
curl -X GET "http://localhost:8000/api/staff?page=1&pageSize=10" \
  -H "Authorization: Bearer $TOKEN"

# 创建订单
curl -X POST "http://localhost:8000/api/orders" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "orderType": "video_purchase",
    "industryType": "movie",
    "visualStyle": "scifi",
    "duration": 120,
    "priceRange": {"min": 5000, "max": 10000},
    "resolution": "4K",
    "size": "1920*1080"
  }'
```

---

### 方式 3: Postman（专业测试工具）

**导入 Postman 集合**:

1. 打开 Postman
2. 点击 "Import"
3. 选择文件: `api-spec/postman_collection.json`
4. 导入成功后会看到所有 API 接口

**使用步骤**:

1. **设置环境变量**:
   - 创建新环境 "Development"
   - 添加变量:
     - `baseUrl`: `http://localhost:8000`
     - `token`: (留空，登录后自动填充)

2. **登录获取 Token**:
   - 打开 "认证 → 登录" 请求
   - 点击 "Send"
   - Token 会自动保存到环境变量

3. **测试其他接口**:
   - 所有请求会自动使用保存的 token

---

### 方式 4: Python 脚本（自动化测试）

创建测试脚本 `test_api.py`:

```python
import requests

BASE_URL = "http://localhost:8000/api"

# 1. 登录
def test_login():
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "123456",
        "role": "admin"
    })
    print("登录响应:", response.json())
    return response.json()["data"]["token"]

# 2. 获取订单列表
def test_get_orders(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/orders", headers=headers)
    print("订单列表:", response.json())

# 3. 创建订单
def test_create_order(token):
    headers = {"Authorization": f"Bearer {token}"}
    order_data = {
        "orderType": "video_purchase",
        "industryType": "movie",
        "visualStyle": "scifi",
        "duration": 120,
        "priceRange": {"min": 5000, "max": 10000},
        "resolution": "4K",
        "size": "1920*1080"
    }
    response = requests.post(f"{BASE_URL}/orders", json=order_data, headers=headers)
    print("创建订单:", response.json())

if __name__ == "__main__":
    # 运行测试
    token = test_login()
    test_get_orders(token)
    test_create_order(token)
```

**运行测试**:
```bash
python test_api.py
```

---

## 4. 前后端联调

### 前提条件

✅ 后端已启动（`http://localhost:8000`）  
✅ 前端已启动（`http://localhost:3000`）

---

### 方式 1: 前端关闭 Mock，直连后端（推荐）

**步骤 1**: 修改前端 API 配置

编辑 `src/utils/api.ts`:

```typescript
// 找到这一行（约第 10 行）
const ENABLE_MOCK = true  // 改为 false

// 修改为：
const ENABLE_MOCK = false  // 关闭 Mock，使用真实后端
```

**步骤 2**: 修改前端请求地址

编辑 `src/utils/request.ts`:

```typescript
// 找到 baseURL 配置（约第 5 行）
const request: AxiosInstance = axios.create({
  baseURL: '/api',  // 默认值
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 改为：
const request: AxiosInstance = axios.create({
  baseURL: 'http://localhost:8000/api',  // 直接指向后端
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})
```

**步骤 3**: 重启前端

```bash
# 停止前端 (Ctrl+C)
# 重新启动
npm run dev
```

**步骤 4**: 测试登录

1. 访问 `http://localhost:3000/login`
2. 输入：`user` / `123456`（普通用户）
3. 或 `http://localhost:3000/admin/login`
4. 输入：`admin` / `123456`（管理员）

**注意**: 可能会遇到 CORS 跨域问题，继续看下面的解决方案。

---

### 方式 2: 配置 Vite 代理（无 CORS 问题）⭐

这是**生产环境推荐**的方式。

**步骤 1**: 编辑 Vite 配置

编辑 `vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    open: true,
    // 添加代理配置 ⭐
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path  // 保持 /api 前缀
      }
    }
  }
})
```

**步骤 2**: 确保前端 API 配置

编辑 `src/utils/request.ts`:

```typescript
const request: AxiosInstance = axios.create({
  baseURL: '/api',  // 使用相对路径，Vite 会自动代理
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})
```

**步骤 3**: 关闭 Mock

编辑 `src/utils/api.ts`:

```typescript
const ENABLE_MOCK = false  // 关闭 Mock
```

**步骤 4**: 重启前端

```bash
# 停止前端 (Ctrl+C)
# 重新启动
npm run dev
```

**工作原理**:
```
前端请求: http://localhost:3000/api/auth/login
    ↓ (Vite 代理)
后端接收: http://localhost:8000/api/auth/login
```

---

### 解决 CORS 跨域问题

如果直连后端时遇到 CORS 错误：

```
Access to XMLHttpRequest at 'http://localhost:8000/api/auth/login' 
from origin 'http://localhost:3000' has been blocked by CORS policy
```

**方案 1**: 配置后端 CORS（已完成）

后端已经配置了 CORS，默认允许 `http://localhost:3000`。

检查 `backend/.env`:
```env
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

如果前端运行在其他端口，添加到这里。

**方案 2**: 使用 Vite 代理（推荐）

按照上面"方式 2"配置 Vite 代理，完全避免 CORS 问题。

---

### 联调测试流程

**完整的联调测试步骤**:

```bash
# Terminal 1: 启动后端
cd backend
./run.sh

# Terminal 2: 启动前端
cd ..  # 回到项目根目录
npm run dev
```

**测试清单**:

1. **✅ 用户注册**
   - 访问 `http://localhost:3000/register`
   - 注册新用户
   - 查看后端日志和数据库

2. **✅ 用户登录**
   - 访问 `http://localhost:3000/login`
   - 登录测试账户
   - 检查 token 是否保存

3. **✅ 管理员登录**
   - 访问 `http://localhost:3000/admin/login`
   - 使用 admin 账户登录
   - 进入管理员界面

4. **✅ 创建订单**
   - 用户工作台 → 选择服务类型
   - 填写订单表单
   - 提交订单
   - 检查后端数据库是否保存

5. **✅ 订单管理**
   - 管理员查看订单列表
   - 分配负责人
   - 更新订单状态
   - 上传预览文件

6. **✅ 负责人管理**
   - 访问 `http://localhost:3000/admin/staff`
   - 添加新负责人
   - 编辑负责人信息
   - 查看订单统计

---

## 5. 常见问题

### Q1: 后端启动失败，提示端口被占用

**错误信息**:
```
ERROR:    [Errno 48] error while attempting to bind on address ('0.0.0.0', 8000): address already in use
```

**解决方案**:
```bash
# 查找占用 8000 端口的进程
lsof -ti:8000

# 杀死进程
kill -9 $(lsof -ti:8000)

# 或者使用其他端口启动
python -m uvicorn app.main:app --reload --port 8001
```

---

### Q2: 数据库错误或需要重置数据库

**重置数据库**:
```bash
cd backend

# 删除现有数据库
rm app.db

# 重新初始化
python scripts/init_admin.py

# 重启服务器
```

---

### Q3: 前端请求后端返回 401 Unauthorized

**可能原因**:
1. Token 过期
2. Token 格式错误
3. 后端 JWT 密钥改变

**解决方案**:
```bash
# 1. 清除前端 localStorage
# 浏览器开发者工具 → Application → Local Storage → Clear

# 2. 重新登录获取新 token

# 3. 检查后端 JWT 配置
# 查看 backend/.env 中的 JWT_SECRET_KEY
```

---

### Q4: 邮件发送失败

**错误信息**:
```
SMTPAuthenticationError: (535, b'Login Fail. Please enter your...
```

**解决方案**:

1. 确认使用的是 **QQ 邮箱授权码**，不是 QQ 密码
2. 获取授权码：
   - 登录 QQ 邮箱
   - 设置 → 账户 → POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务
   - 开启"SMTP服务"
   - 生成授权码

3. 更新 `.env`:
   ```env
   SMTP_PASSWORD=你的16位授权码
   ```

4. 重启后端服务器

---

### Q5: Swagger UI 显示但无法测试

**检查**:
1. 后端是否正确启动
2. 访问 `http://localhost:8000/docs`（注意是 8000 端口）
3. 检查浏览器控制台是否有错误

---

### Q6: 前后端联调时请求一直 pending

**可能原因**:
- 后端服务未启动
- 端口号错误
- 防火墙拦截

**解决方案**:
```bash
# 1. 确认后端正在运行
curl http://localhost:8000/

# 2. 检查前端配置的后端地址
# 查看 src/utils/request.ts 中的 baseURL

# 3. 检查浏览器网络面板
# 开发者工具 → Network → 查看请求详情
```

---

## 📊 调试工具推荐

### 浏览器开发者工具

**Network 面板**:
- 查看所有 HTTP 请求
- 检查请求头、响应体
- 查看状态码和耗时

**Console 面板**:
- 查看前端日志
- 检查 JavaScript 错误

**Application 面板**:
- 查看 localStorage（token 存储位置）
- 清除缓存和存储

---

### 后端日志

**查看日志**:
```bash
# 后端运行时的终端会实时显示日志

# 示例日志：
INFO:     127.0.0.1:54321 - "POST /api/auth/login HTTP/1.1" 200 OK
INFO:     127.0.0.1:54322 - "GET /api/orders HTTP/1.1" 200 OK
INFO:     127.0.0.1:54323 - "POST /api/orders HTTP/1.1" 201 Created
```

**日志级别**:
- `INFO`: 一般信息
- `WARNING`: 警告
- `ERROR`: 错误

---

### 数据库查看

**方式 1: SQLite 浏览器**

下载 [DB Browser for SQLite](https://sqlitebrowser.org/)

打开 `backend/app.db` 查看数据。

**方式 2: 命令行**

```bash
cd backend

# 打开数据库
sqlite3 app.db

# 查看所有表
.tables

# 查看用户表
SELECT * FROM users;

# 查看订单表
SELECT * FROM orders;

# 退出
.quit
```

---

## 🎯 测试检查清单

### 后端独立测试

- [ ] 后端成功启动（http://localhost:8000）
- [ ] Swagger UI 可访问（http://localhost:8000/docs）
- [ ] 登录接口返回 token
- [ ] 获取订单列表（需要 token）
- [ ] 创建订单成功
- [ ] 更新订单状态成功
- [ ] 负责人列表可获取
- [ ] 添加负责人成功

### 前后端联调测试

- [ ] 前端可以正常登录
- [ ] Token 正确保存到 localStorage
- [ ] 订单列表可以显示
- [ ] 创建订单成功并在后端数据库中查到
- [ ] 管理员可以分配负责人
- [ ] 订单状态更新同步到前端
- [ ] 文件上传功能正常（Mock 或真实）

---

## 🚀 快速命令参考

```bash
# === 后端 ===
cd backend
./run.sh                          # 快速启动（推荐）
source venv/bin/activate          # 激活虚拟环境
python -m uvicorn app.main:app --reload  # 启动服务器
python scripts/init_admin.py      # 重置数据库
python scripts/backup_db.py       # 备份数据库

# === 前端 ===
npm run dev                       # 启动开发服务器
npm run build                     # 生产构建
npm run preview                   # 预览生产构建

# === 测试 ===
curl http://localhost:8000/       # 测试后端
curl http://localhost:3000/       # 测试前端

# === 数据库 ===
sqlite3 backend/app.db            # 打开数据库
rm backend/app.db                 # 删除数据库（重置）
```

---

## 📞 获取帮助

**文档**:
- 后端详细文档: `backend/README.md`
- API 规范: `api-spec/openapi.yaml`
- 部署指南: `docs/DEPLOYMENT_GUIDE.md`

**在线资源**:
- FastAPI 官方文档: https://fastapi.tiangolo.com/
- Vue 3 官方文档: https://vuejs.org/
- Element Plus: https://element-plus.org/

---

**祝测试顺利！** 🎉

