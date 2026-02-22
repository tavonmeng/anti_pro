#!/bin/bash
# 自动设置环境变量并启动 Unique Vision 网站

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
TOOLS_DIR="$SCRIPT_DIR/tools"
NODE_BIN=""

# ── 1. 优先查找 tools/ 目录中的本地 Node.js ─────────────────────────────
# 自动检测 CPU 架构（Apple Silicon: arm64, Intel: x64）
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
  LOCAL_NODE="$TOOLS_DIR/node-v22.13.0-darwin-arm64/bin/node"
else
  LOCAL_NODE="$TOOLS_DIR/node-v22.13.0-darwin-x64/bin/node"
fi

if [ -x "$LOCAL_NODE" ]; then
  NODE_BIN="$(dirname "$LOCAL_NODE")"
  echo "✅ 使用本地 Node.js ($ARCH): $LOCAL_NODE"
fi

# ── 2. 回退：查找系统 Node.js ─────────────────────────────────────────────
if [ -z "$NODE_BIN" ]; then
  for candidate in \
    /opt/homebrew/bin \
    /usr/local/bin \
    "$HOME/.volta/bin" \
    "$HOME/.nvm/versions/node/"*/bin; do
    if [ -x "$candidate/node" ]; then
      NODE_BIN="$candidate"
      echo "✅ 使用系统 Node.js: $candidate/node"
      break
    fi
  done
fi

# ── 3. 找不到则报错并提示 ────────────────────────────────────────────────
if [ -z "$NODE_BIN" ]; then
  echo ""
  echo "❌ 错误: 未找到 Node.js。"
  echo "   请在 https://nodejs.org 下载安装，或确保 tools/ 目录完整。"
  exit 1
fi

# 注入 PATH
export PATH="$NODE_BIN:$PATH"
echo "   Node.js $(node --version) | npm $(npm --version)"
echo ""

# ── 4. 进入网站目录 ──────────────────────────────────────────────────────
cd "$SCRIPT_DIR/website"

# ── 5. 安装依赖 ──────────────────────────────────────────────────────────
if [ ! -d "node_modules" ]; then
  echo "📦 正在安装依赖..."
  npm install
fi

# ── 6. 启动开发服务器 ────────────────────────────────────────────────────
echo "🚀 启动开发服务器: http://localhost:5173"
npm run dev
