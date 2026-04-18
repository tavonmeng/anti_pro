# 快速诊断指南

## 已添加调试日志

我已经在 `src/utils/request.ts` 中添加了详细的调试日志。现在请按以下步骤操作：

### 1. 刷新浏览器页面

按 `Ctrl+Shift+R` (Windows/Linux) 或 `Cmd+Shift+R` (Mac) 强制刷新页面

### 2. 打开浏览器开发者工具

按 `F12` 或右键点击页面 → "检查"

### 3. 切换到 Console 标签

查看控制台输出

### 4. 尝试注册

填写注册表单并提交

### 5. 查看控制台输出

你应该能看到以下日志之一：

#### 情况 A: 成功响应
```
Response received: {code: 200, message: "注册成功", data: {success: true}}
```

#### 情况 B: API 错误（code 不是 200）
```
API Error: {code: 400, message: "...", data: {...}}
```

#### 情况 C: HTTP 错误
```
Request error: ...
Error response: {status: 404, data: {...}}
```

#### 情况 D: 网络错误
```
Request error: ...
No response received: ...
```

### 6. 切换到 Network 标签

1. 点击 Network 标签
2. 刷新页面（清除之前的请求）
3. 再次尝试注册
4. 找到 `register` 或 `auth/register` 请求
5. 点击查看详细信息

**检查以下内容**：

- **Request URL**: 应该是 `http://localhost:3000/api/auth/register`
- **Request Method**: 应该是 `POST`
- **Status Code**: 
  - `200` = 成功
  - `404` = 路径错误
  - `500` = 服务器错误
  - `CORS error` = CORS 配置问题
  - `(failed)` = 网络连接失败

- **Request Headers**:
  ```
  Content-Type: application/json
  ```

- **Request Payload**:
  ```json
  {
    "username": "...",
    "email": "...",
    "password": "...",
    "role": "user"
  }
  ```

- **Response**:
  - 成功: `{"code":200,"message":"注册成功","data":{"success":true}}`
  - 错误: `{"detail":"..."}` 或 `{"message":"..."}`

## 常见问题快速检查

### 问题 1: 控制台显示 "网络连接失败"

**原因**: 后端服务未启动或无法连接

**解决**:
```bash
# 检查后端服务
curl http://localhost:8000/health

# 如果无法连接，启动后端
cd backend
./run.sh
```

### 问题 2: 控制台显示 "请求地址不存在" 或 404

**原因**: API 路径错误或代理配置问题

**检查**:
- 确认请求 URL 是 `http://localhost:3000/api/auth/register`
- 确认 `vite.config.ts` 中有代理配置
- **重启前端服务**（修改 vite.config.ts 后必须重启）

### 问题 3: 控制台显示 CORS 错误

**原因**: 后端 CORS 配置不允许前端源

**解决**:
检查 `backend/app/config.py` 中的 `CORS_ORIGINS` 配置：
```python
CORS_ORIGINS: Union[List[str], str] = [
    "http://localhost:3000",  # 确保包含前端地址
    "http://localhost:5173"
]
```

### 问题 4: 控制台显示 "API Error" 且 code 不是 200

**原因**: 后端返回了错误响应

**检查**:
- 查看控制台中的 `API Error` 日志
- 查看具体的 `code` 和 `message`
- 检查后端日志

### 问题 5: 控制台没有任何日志

**原因**: 请求可能没有发送

**检查**:
- 确认表单验证已通过
- 确认验证码已通过验证
- 查看 Network 标签，确认请求是否发送

## 请提供以下信息

如果问题仍然存在，请提供：

1. **浏览器控制台的完整输出**（Console 标签）
   - 复制所有错误信息和日志

2. **Network 标签中的请求详情**
   - 请求 URL
   - 请求方法
   - 状态码
   - 请求头
   - 请求体
   - 响应内容

3. **后端服务日志**
   - 查看后端控制台的输出

4. **具体错误信息**
   - 页面上显示的具体错误消息

---

**下一步**: 刷新页面，打开控制台，尝试注册，然后告诉我控制台显示的具体信息。


