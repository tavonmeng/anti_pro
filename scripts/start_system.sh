#!/bin/bash
# 启动整个系统 (合并后的前端 + 后端)

# 获取脚本所在根目录绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"

echo "================================================="
echo "  🚀 本地测试全系统启动脚本"
echo "================================================="

# 捕获 Ctrl+C 并杀死所有后台进程（包含处理 Uvicorn reload 导致的孤儿进程占用 8000 端口）
trap 'echo -e "\n🛑 正在停止所有服务..."; pkill -P $$; lsof -t -i:8000 | xargs kill -9 2>/dev/null; lsof -t -i:3000 | xargs kill -9 2>/dev/null; exit' SIGINT SIGTERM EXIT

# 尝试检测并使用本地指定 Node 版本
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
  LOCAL_NODE="$SCRIPT_DIR/tools/node-v22.13.0-darwin-arm64/bin/node"
else
  LOCAL_NODE="$SCRIPT_DIR/tools/node-v22.13.0-darwin-x64/bin/node"
fi

if [ -x "$LOCAL_NODE" ]; then
  NODE_BIN="$(dirname "$LOCAL_NODE")"
  export PATH="$NODE_BIN:$PATH"
fi

# ── 1. 启动前端 (官网 + 管理系统已合并) ────────────────────────
echo "📦 [1/2] 正在启动前端应用 (官网 + 管理系统) ..."
cd "$SCRIPT_DIR/cursor_sh"
if [ ! -d "node_modules" ]; then
  npm install
fi

# 启动前端 (后台)
npm run dev -- --port 3000 &
FE_PID=$!
echo "✅ 前端已启动 (PID: $FE_PID)"

# ── 2. 启动后端 (cursor_sh/backend) ────────────────────────────
echo "📦 [2/2] 正在启动后端 (cursor_sh/backend) ..."
cd "$SCRIPT_DIR/cursor_sh/backend"

# 简单的Python虚拟环境激活并启动
if [ ! -d "venv" ]; then
  echo "📦 创建 Python 虚拟环境..."
  python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1

# 启动后端 (后台)
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BE_PID=$!
echo "✅ 后端已启动 (PID: $BE_PID)"

echo "================================================="
echo "✅ 所有服务已在后台运行！"
echo "🌐 1. 官网首页: http://localhost:3000"
echo "🔐 2. 用户登录: http://localhost:3000/login"
echo "⚙️  3. 后端接口: http://localhost:8000/docs"
echo "🛑 按下 [Ctrl+C] 组合键即可同时停止所有服务"
echo "================================================="

# 挂起当前脚本以维持子进程存活
wait
