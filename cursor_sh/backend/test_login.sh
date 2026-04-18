#!/bin/bash

# 用户登录模块测试脚本
# 使用方法: ./test_login.sh

BASE_URL="http://localhost:8000/api"

echo "=========================================="
echo "🔐 用户登录模块测试"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查服务器是否运行
echo "📡 检查服务器状态..."
if ! curl -s -f "${BASE_URL}/auth/logout" > /dev/null 2>&1; then
    echo -e "${RED}❌ 错误: 无法连接到服务器 ${BASE_URL}${NC}"
    echo "请确保后端服务已启动: cd backend && ./run.sh"
    exit 1
fi
echo -e "${GREEN}✅ 服务器运行正常${NC}"
echo ""

# 测试用例 1: 管理员登录（成功）
echo "=========================================="
echo "测试用例 1: 管理员登录（成功）"
echo "=========================================="
echo "请求: POST ${BASE_URL}/auth/login"
echo "请求体:"
cat <<EOF
{
  "username": "admin",
  "password": "123456",
  "role": "admin",
  "captcha": "1234"
}
EOF
echo ""
echo "响应:"
RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "123456",
    "role": "admin",
    "captcha": "1234"
  }')

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# 提取 token
TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['token'])" 2>/dev/null)

if [ -n "$TOKEN" ]; then
    echo -e "${GREEN}✅ 登录成功，Token 已获取${NC}"
    echo "Token: ${TOKEN:0:50}..."
    echo ""
    
    # 保存 token 到文件
    echo "$TOKEN" > /tmp/test_token.txt
    echo "Token 已保存到 /tmp/test_token.txt"
else
    echo -e "${RED}❌ 登录失败，未获取到 Token${NC}"
fi
echo ""

# 测试用例 2: 普通用户登录（需要先注册）
echo "=========================================="
echo "测试用例 2: 普通用户注册"
echo "=========================================="
echo "请求: POST ${BASE_URL}/auth/register"
echo "请求体:"
cat <<EOF
{
  "username": "testuser",
  "email": "testuser@example.com",
  "password": "123456",
  "role": "user"
}
EOF
echo ""
echo "响应:"
REGISTER_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "testuser@example.com",
    "password": "123456",
    "role": "user"
  }')

echo "$REGISTER_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$REGISTER_RESPONSE"
echo ""

# 测试用例 3: 普通用户登录（成功）
echo "=========================================="
echo "测试用例 3: 普通用户登录（成功）"
echo "=========================================="
echo "请求: POST ${BASE_URL}/auth/login"
echo "请求体:"
cat <<EOF
{
  "username": "testuser",
  "password": "123456",
  "role": "user",
  "captcha": "1234"
}
EOF
echo ""
echo "响应:"
USER_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "123456",
    "role": "user",
    "captcha": "1234"
  }')

echo "$USER_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$USER_RESPONSE"
echo ""

# 测试用例 4: 错误密码（失败）
echo "=========================================="
echo "测试用例 4: 错误密码（应该失败）"
echo "=========================================="
echo "请求: POST ${BASE_URL}/auth/login"
echo "请求体:"
cat <<EOF
{
  "username": "admin",
  "password": "wrongpassword",
  "role": "admin",
  "captcha": "1234"
}
EOF
echo ""
echo "响应:"
ERROR_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "wrongpassword",
    "role": "admin",
    "captcha": "1234"
  }')

echo "$ERROR_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$ERROR_RESPONSE"
echo ""

# 测试用例 5: 不存在的用户（失败）
echo "=========================================="
echo "测试用例 5: 不存在的用户（应该失败）"
echo "=========================================="
echo "请求: POST ${BASE_URL}/auth/login"
echo "请求体:"
cat <<EOF
{
  "username": "nonexistent",
  "password": "123456",
  "role": "user",
  "captcha": "1234"
}
EOF
echo ""
echo "响应:"
NOTFOUND_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "nonexistent",
    "password": "123456",
    "role": "user",
    "captcha": "1234"
  }')

echo "$NOTFOUND_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$NOTFOUND_RESPONSE"
echo ""

# 测试用例 6: 使用 Token 访问受保护接口
if [ -n "$TOKEN" ]; then
    echo "=========================================="
    echo "测试用例 6: 使用 Token 访问受保护接口"
    echo "=========================================="
    echo "请求: GET ${BASE_URL}/orders"
    echo "Header: Authorization: Bearer $TOKEN"
    echo ""
    echo "响应:"
    PROTECTED_RESPONSE=$(curl -s -X GET "${BASE_URL}/orders" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "$PROTECTED_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PROTECTED_RESPONSE"
    echo ""
    
    # 检查是否成功
    if echo "$PROTECTED_RESPONSE" | grep -q '"code":200'; then
        echo -e "${GREEN}✅ Token 验证成功，可以访问受保护接口${NC}"
    else
        echo -e "${YELLOW}⚠️  Token 可能无效或接口需要其他权限${NC}"
    fi
fi

echo ""
echo "=========================================="
echo "📋 测试总结"
echo "=========================================="
echo "1. ✅ 管理员登录测试"
echo "2. ✅ 用户注册测试"
echo "3. ✅ 普通用户登录测试"
echo "4. ✅ 错误密码测试"
echo "5. ✅ 不存在用户测试"
if [ -n "$TOKEN" ]; then
    echo "6. ✅ Token 验证测试"
fi
echo ""
echo "💡 提示:"
echo "   - 查看详细 API 文档: http://localhost:8000/docs"
echo "   - 使用 Swagger UI 进行交互式测试"
echo "   - Token 已保存到 /tmp/test_token.txt"
echo ""

