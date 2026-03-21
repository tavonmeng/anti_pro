#!/bin/bash
# 快速修复 npm 依赖问题（rollup 可选依赖问题）

set -e

echo "=========================================="
echo "  修复 npm 依赖问题"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否在项目根目录
if [ ! -f "package.json" ]; then
    echo -e "${RED}错误: 请在项目根目录运行此脚本${NC}"
    exit 1
fi

echo -e "${YELLOW}步骤 1: 清理旧的依赖...${NC}"
if [ -d "node_modules" ]; then
    rm -rf node_modules
    echo -e "${GREEN}已删除 node_modules${NC}"
fi

if [ -f "package-lock.json" ]; then
    rm -f package-lock.json
    echo -e "${GREEN}已删除 package-lock.json${NC}"
fi

echo -e "${YELLOW}步骤 2: 重新安装依赖...${NC}"
npm install

echo -e "${YELLOW}步骤 3: 验证 rollup 是否正常工作...${NC}"
if node -e "require('rollup')" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ rollup 依赖正常${NC}"
else
    echo -e "${YELLOW}尝试强制安装 rollup 依赖...${NC}"
    npm install @rollup/rollup-linux-x64-gnu --save-optional || true
    npm install --force
fi

echo -e "${YELLOW}步骤 4: 测试构建...${NC}"
if npm run build > /tmp/build-test.log 2>&1; then
    echo -e "${GREEN}✓ 构建测试成功${NC}"
else
    echo -e "${YELLOW}完整构建失败，尝试跳过类型检查...${NC}"
    if npx vite build > /tmp/build-test.log 2>&1; then
        echo -e "${GREEN}✓ 构建成功（跳过类型检查）${NC}"
    else
        echo -e "${RED}构建失败，错误日志：${NC}"
        tail -50 /tmp/build-test.log
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}=========================================="
echo "  依赖修复完成！"
echo "==========================================${NC}"






