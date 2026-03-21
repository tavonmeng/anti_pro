# Vite 代理调试指南

## 已修复

✅ 已改回使用 Vite 代理（baseURL: '/api'）
✅ 简化了代理配置，使用标准的 `/api` 匹配模式

## 调试步骤

### 1. 重启前端服务（必须！）

```bash
# 停止当前服务（Ctrl+C）
npm run dev
```

### 2. 检查前端服务控制台

启动后，查看运行 `npm run dev` 的终端，确认：
- Vite 启动成功
- 没有代理相关的错误
- 端口 3000 正在监听

### 3. 测试代理是否工作

在浏览器控制台执行：

```javascript
// 测试健康检查接口
fetch('/api/health')
  .then(r => r.json())
  .then(data => {
    console.log('✅ 代理工作正常:', data);
  })
  .catch(err => {
    console.error('❌ 代理失败:', err);
  });
```

**期望结果**: 应该返回 `{status: "ok", app: "AI设计任务管理系统"}`

### 4. 测试注册接口

在浏览器控制台执行：

```javascript
fetch('/api/auth/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    username: 'testproxy',
    email: 'testproxy@test.com',
    password: '123456',
    role: 'user'
  })
})
  .then(r => r.json())
  .then(data => {
    console.log('✅ 注册请求成功:', data);
  })
  .catch(err => {
    console.error('❌ 注册请求失败:', err);
  });
```

### 5. 检查网络请求

1. 打开浏览器开发者工具（F12）
2. 切换到 Network 标签
3. 尝试注册
4. 查看请求详情：
   - **请求 URL**: 应该是 `http://localhost:3000/api/auth/register`
   - **状态码**: 应该是 `200` 或 `409`
   - **响应**: 查看响应内容

### 6. 检查后端日志

查看后端服务控制台，确认：
- 是否收到请求
- 是否有错误信息

## 常见问题

### 问题 1: 代理不工作，返回 404

**可能原因**:
- 前端服务没有重启
- 代理配置格式错误

**解决**:
1. 确认前端服务已重启
2. 检查 `vite.config.ts` 中的代理配置

### 问题 2: 代理不工作，返回 500

**可能原因**:
- 后端服务未启动
- 后端服务端口不是 8000

**解决**:
```bash
# 检查后端服务
curl http://localhost:8000/health

# 如果无法连接，启动后端
cd backend
./run.sh
```

### 问题 3: CORS 错误

**可能原因**:
- 后端 CORS 配置不允许 `http://localhost:3000`

**解决**:
检查 `backend/app/config.py` 中的 `CORS_ORIGINS` 配置

### 问题 4: 代理配置不生效

**可能原因**:
- Vite 版本问题
- 配置文件格式错误

**解决**:
1. 确认 Vite 版本 >= 5.0
2. 检查配置文件语法

## 当前配置

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    secure: false,
  }
}
```

这个配置会将所有 `/api/*` 请求转发到 `http://localhost:8000/api/*`

## 下一步

1. 重启前端服务
2. 测试代理是否工作
3. 如果还有问题，告诉我具体的错误信息


