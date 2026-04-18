# Vite 代理问题修复

## 问题描述
前端请求返回 500 错误，但后端服务没有收到请求，说明 Vite 代理没有正确转发请求。

## 已修复
✅ 简化了 Vite 代理配置，移除了可能导致问题的 `configure` 选项

## 重要：必须重启前端服务

**修改 `vite.config.ts` 后必须重启前端服务才能生效！**

### 重启步骤：

1. **停止当前前端服务**
   - 在运行 `npm run dev` 的终端窗口按 `Ctrl+C`

2. **重新启动前端服务**
   ```bash
   npm run dev
   ```

3. **确认代理配置生效**
   - 查看终端输出，应该能看到 Vite 启动信息
   - 确认没有代理相关的错误

## 测试步骤

1. **重启前端服务后**，打开浏览器
2. 打开开发者工具（F12）
3. 切换到 Network 标签
4. 尝试注册新用户
5. 查看请求：
   - 请求 URL 应该是：`http://localhost:3000/api/auth/register`
   - 状态码应该是：`200`（成功）或 `409`（用户名已存在）
   - 如果仍然是 500，查看后端控制台的错误日志

## 如果问题仍然存在

### 检查后端日志
查看后端服务的控制台输出，确认：
- 是否有请求到达后端
- 是否有错误信息

### 检查代理是否工作
在浏览器控制台执行：
```javascript
fetch('/api/health', { method: 'GET' })
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
```

应该返回：`{status: "ok", app: "AI设计任务管理系统"}`

### 直接测试后端
```bash
curl http://localhost:8000/api/health
```

应该返回：`{"status":"ok","app":"AI设计任务管理系统"}`

---

**关键点**：修改 `vite.config.ts` 后必须重启前端服务！


