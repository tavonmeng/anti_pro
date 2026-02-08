#!/bin/bash
# 自动设置环境变量并启动 Unique Vision 网站

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# 设置 Node.js 环境 (使用本地安装的 Node v22)
export PATH="$SCRIPT_DIR/tools/node-v22.13.0-darwin-x64/bin:$PATH"

# 检查 Node 是否可用
if ! command -v node &> /dev/null; then
    echo "错误: 未找到 Node.js。请确保 'tools' 目录完整。"
    exit 1
fi

echo "Environment Ready: $(node --version)"
echo "Starting Website..."

# 进入网站目录
cd "$SCRIPT_DIR/website"

# 安装依赖 (如果 node_modules 不存在)
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# 启动开发服务器
echo "Application running at: http://localhost:5173"
npm run dev
