#!/bin/bash
# 启动整个系统 (官网 + Cursor系统的后端与前端)

# 获取脚本所在根目录绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"

echo "================================================="
echo "  🚀 本地测试全系统启动脚本"
echo "================================================="

# 捕获 Ctrl+C 并杀死所有后台进程
trap 'echo "\n🛑 正在停止所有服务..."; pkill -P $$; exit' SIGINT SIGTERM EXIT

# ── 1. 启动项目官网 (website) ───────────────────────────────────
echo "📦 [1/3] 正在启动官网前端 (website) ..."
cd "$SCRIPT_DIR/website"

# 尝试检测并使用本地指定 Node 版本 (参考自 start_website.sh)
NODE_BIN=""
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

if [ ! -d "node_modules" ]; then
  npm install
fi

# 启动官网 (后台)
npm run dev &
WEBSITE_PID=$!
echo "✅ 官网已启动 (PID: $WEBSITE_PID)"

# ── 2. 启动 Cursor系统前端 (cursor_sh frontend) ────────────────
echo "📦 [2/3] 正在启动系统前端 (cursor_sh) ..."
cd "$SCRIPT_DIR/cursor_sh"
if [ ! -d "node_modules" ]; then
  npm install
fi

# 启动系统前端 (后台)
npm run dev -- --port 3000 &
CURSOR_FE_PID=$!
echo "✅ 系统前端已启动 (PID: $CURSOR_FE_PID)"

# ── 3. 启动 Cursor系统后端 (cursor_sh backend) ─────────────────
echo "📦 [3/3] 正在启动系统后端 (cursor_sh/backend) ..."
cd "$SCRIPT_DIR/cursor_sh/backend"

# 简单的Python虚拟环境激活并启动
if [ ! -d "venv" ]; then
  echo "📦 创建 Python 虚拟环境..."
  python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1

# 启动系统后端 (后台)
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
CURSOR_BE_PID=$!
echo "✅ 系统后端已启动 (PID: $CURSOR_BE_PID)"

echo "================================================="
echo "✅ 所有系统服务已在后台运行！"
echo "🌐 1. 官网浏览: http://localhost:5173"
echo "💻 2. 登录平台: http://localhost:3000"
echo "⚙️  3. 后端接口: http://localhost:8000/docs"
echo "🛑 按下 [Ctrl+C] 组合键即可同时停止所有服务"
echo "================================================="

# 挂起当前脚本以维持子进程存活
wait
