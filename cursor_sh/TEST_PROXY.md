# 测试 Vite 代理

## 问题
前端请求返回 500，但后端没有收到请求，说明 Vite 代理没有正确转发。

## 已添加代理调试日志

我已经在 `vite.config.ts` 中添加了代理调试日志。现在需要：

### 1. 重启前端服务（必须！）

```bash
# 停止当前服务（Ctrl+C）
# 重新启动
npm run dev
```

### 2. 查看前端服务控制台

重启后，前端服务的控制台（运行 `npm run dev` 的终端）应该会显示代理日志：
- `Vite proxying: POST /api/auth/register -> /api/auth/register`
- `Vite proxy response: 200 /api/auth/register`

如果没有看到这些日志，说明代理没有工作。

### 3. 测试代理

在浏览器控制台执行：

```javascript
fetch('/api/health')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
```

应该返回：`{status: "ok", app: "AI设计任务管理系统"}`

### 4. 如果代理仍然不工作

可能需要检查：
1. 前端服务是否真的重启了
2. Vite 版本是否支持代理配置
3. 是否有其他配置冲突

## 临时解决方案

如果代理一直不工作，可以临时修改前端请求的 baseURL：

**文件**: `src/utils/request.ts`

```typescript
const request: AxiosInstance = axios.create({
  baseURL: 'http://localhost:8000/api',  // 直接指向后端
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})
```

**注意**: 这只是临时方案，生产环境需要配置正确的代理或 CORS。


