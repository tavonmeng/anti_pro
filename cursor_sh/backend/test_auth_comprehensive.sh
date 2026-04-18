#!/bin/bash

# 用户登录和注册模块综合测试脚本
# 测试完成后会检查数据库确认注册结果

BASE_URL="http://localhost:8000/api"
DB_PATH="./app.db"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试结果
PASSED=0
FAILED=0
TEST_USERNAME=""
TEST_EMAIL=""

print_section() {
    echo ""
    echo "============================================================"
    echo "  $1"
    echo "============================================================"
}

print_test() {
    local name=$1
    local status=$2
    local details=$3
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ $name${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ $name${NC}"
        ((FAILED++))
    fi
    
    if [ -n "$details" ]; then
        echo "   $details"
    fi
}

# 测试用例 1: 管理员登录
test_admin_login() {
    print_section "测试用例 1: 管理员登录"
    
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
    
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
            "username": "admin",
            "password": "123456",
            "role": "admin",
            "captcha": "1234"
        }')
    
    HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')
    
    echo "响应 (HTTP $HTTP_CODE):"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    
    if [ "$HTTP_CODE" = "200" ]; then
        TOKEN=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('data', {}).get('token', ''))" 2>/dev/null)
        USERNAME=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('data', {}).get('user', {}).get('username', ''))" 2>/dev/null)
        
        if [ -n "$TOKEN" ] && [ -n "$USERNAME" ]; then
            print_test "管理员登录" "PASS" "Token: ${TOKEN:0:50}... | 用户: $USERNAME"
            echo "$TOKEN" > /tmp/admin_token.txt
            return 0
        else
            print_test "管理员登录" "FAIL" "响应中缺少 token 或 user 信息"
            return 1
        fi
    else
        print_test "管理员登录" "FAIL" "HTTP $HTTP_CODE"
        return 1
    fi
}

# 测试用例 2: 用户注册
test_user_register() {
    print_section "测试用例 2: 用户注册"
    
    # 生成唯一的用户名
    TIMESTAMP=$(date +%Y%m%d%H%M%S)
    TEST_USERNAME="testuser_${TIMESTAMP}"
    TEST_EMAIL="${TEST_USERNAME}@test.com"
    
    echo "请求: POST ${BASE_URL}/auth/register"
    echo "请求体:"
    cat <<EOF
{
  "username": "$TEST_USERNAME",
  "email": "$TEST_EMAIL",
  "password": "123456",
  "role": "user"
}
EOF
    echo ""
    
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/auth/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"$TEST_USERNAME\",
            \"email\": \"$TEST_EMAIL\",
            \"password\": \"123456\",
            \"role\": \"user\"
        }")
    
    HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')
    
    echo "响应 (HTTP $HTTP_CODE):"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    
    if [ "$HTTP_CODE" = "200" ]; then
        CODE=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('code', 0))" 2>/dev/null)
        if [ "$CODE" = "200" ]; then
            print_test "用户注册" "PASS" "用户名: $TEST_USERNAME | 邮箱: $TEST_EMAIL"
            echo "$TEST_USERNAME" > /tmp/test_username.txt
            echo "$TEST_EMAIL" > /tmp/test_email.txt
            return 0
        else
            print_test "用户注册" "FAIL" "响应 code 不是 200"
            return 1
        fi
    else
        print_test "用户注册" "FAIL" "HTTP $HTTP_CODE"
        return 1
    fi
}

# 测试用例 3: 新注册用户登录
test_new_user_login() {
    local username=$1
    
    print_section "测试用例 3: 新注册用户登录"
    
    if [ -z "$username" ]; then
        print_test "新用户登录" "FAIL" "跳过：用户未成功注册"
        return 1
    fi
    
    echo "请求: POST ${BASE_URL}/auth/login"
    echo "请求体:"
    cat <<EOF
{
  "username": "$username",
  "password": "123456",
  "role": "user",
  "captcha": "1234"
}
EOF
    echo ""
    
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/auth/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"$username\",
            \"password\": \"123456\",
            \"role\": \"user\",
            \"captcha\": \"1234\"
        }")
    
    HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')
    
    echo "响应 (HTTP $HTTP_CODE):"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    
    if [ "$HTTP_CODE" = "200" ]; then
        TOKEN=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('data', {}).get('token', ''))" 2>/dev/null)
        if [ -n "$TOKEN" ]; then
            print_test "新用户登录" "PASS" "Token: ${TOKEN:0:50}..."
            return 0
        else
            print_test "新用户登录" "FAIL" "响应中缺少 token"
            return 1
        fi
    else
        print_test "新用户登录" "FAIL" "HTTP $HTTP_CODE"
        return 1
    fi
}

# 测试用例 4: 错误密码
test_wrong_password() {
    print_section "测试用例 4: 错误密码（应该失败）"
    
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
            "username": "admin",
            "password": "wrongpassword",
            "role": "admin",
            "captcha": "1234"
        }')
    
    HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')
    
    echo "响应 (HTTP $HTTP_CODE):"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    
    if [ "$HTTP_CODE" = "401" ]; then
        print_test "错误密码测试" "PASS" "正确返回 401 未授权错误"
        return 0
    else
        print_test "错误密码测试" "FAIL" "应该返回 401，实际返回 $HTTP_CODE"
        return 1
    fi
}

# 测试用例 5: 不存在用户
test_nonexistent_user() {
    print_section "测试用例 5: 不存在用户（应该失败）"
    
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
            "username": "nonexistent_user_12345",
            "password": "123456",
            "role": "user",
            "captcha": "1234"
        }')
    
    HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')
    
    echo "响应 (HTTP $HTTP_CODE):"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    
    if [ "$HTTP_CODE" = "401" ]; then
        print_test "不存在用户测试" "PASS" "正确返回 401 未授权错误"
        return 0
    else
        print_test "不存在用户测试" "FAIL" "应该返回 401，实际返回 $HTTP_CODE"
        return 1
    fi
}

# 测试用例 6: 重复用户名注册
test_duplicate_username() {
    print_section "测试用例 6: 重复用户名注册（应该失败）"
    
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "${BASE_URL}/auth/register" \
        -H "Content-Type: application/json" \
        -d '{
            "username": "admin",
            "email": "admin2@test.com",
            "password": "123456",
            "role": "user"
        }')
    
    HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')
    
    echo "响应 (HTTP $HTTP_CODE):"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    
    if [ "$HTTP_CODE" = "409" ]; then
        print_test "重复用户名测试" "PASS" "正确返回 409 冲突错误"
        return 0
    else
        print_test "重复用户名测试" "FAIL" "应该返回 409，实际返回 $HTTP_CODE"
        return 1
    fi
}

# 数据库验证
check_database() {
    local username=$1
    local email=$2
    
    print_section "数据库验证: 检查注册用户"
    
    if [ -z "$username" ] || [ ! -f "$DB_PATH" ]; then
        print_test "数据库验证" "FAIL" "用户名为空或数据库文件不存在"
        return 1
    fi
    
    # 使用 Python 查询数据库
    RESULT=$(python3 <<EOF
import sqlite3
import sys

try:
    conn = sqlite3.connect("$DB_PATH")
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, username, email, role, is_active, created_at FROM users WHERE username = ?",
        ("$username",)
    )
    user = cursor.fetchone()
    
    if user:
        user_id, db_username, db_email, role, is_active, created_at = user
        print(f"SUCCESS|{user_id}|{db_username}|{db_email}|{role}|{is_active}|{created_at}")
    else:
        print("NOT_FOUND")
    
    conn.close()
except Exception as e:
    print(f"ERROR|{str(e)}")
    sys.exit(1)
EOF
)
    
    if echo "$RESULT" | grep -q "SUCCESS"; then
        IFS='|' read -r status user_id db_username db_email role is_active created_at <<< "$RESULT"
        print_test "数据库验证" "PASS" "用户ID: $user_id | 用户名: $db_username | 邮箱: $db_email | 角色: $role | 状态: $([ "$is_active" = "1" ] && echo "激活" || echo "禁用") | 创建时间: $created_at"
        
        # 验证数据一致性
        if [ "$db_username" = "$username" ] && [ "$db_email" = "$email" ]; then
            print_test "数据一致性验证" "PASS" "数据库中的用户名和邮箱与注册信息一致"
            return 0
        else
            print_test "数据一致性验证" "FAIL" "数据不匹配: 期望($username, $email), 实际($db_username, $db_email)"
            return 1
        fi
    elif echo "$RESULT" | grep -q "NOT_FOUND"; then
        print_test "数据库验证" "FAIL" "数据库中未找到用户: $username"
        return 1
    else
        print_test "数据库验证" "FAIL" "数据库查询异常: $RESULT"
        return 1
    fi
}

# 测试用例 7: Token验证
test_token_validation() {
    print_section "测试用例 7: Token验证（访问受保护接口）"
    
    if [ ! -f "/tmp/admin_token.txt" ]; then
        print_test "Token验证" "FAIL" "跳过：未获取到有效Token"
        return 1
    fi
    
    TOKEN=$(cat /tmp/admin_token.txt)
    
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "${BASE_URL}/orders" \
        -H "Authorization: Bearer $TOKEN")
    
    HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')
    
    echo "响应 (HTTP $HTTP_CODE):"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_test "Token验证" "PASS" "Token有效，可以访问受保护接口"
        return 0
    elif [ "$HTTP_CODE" = "401" ]; then
        print_test "Token验证" "FAIL" "Token无效或已过期"
        return 1
    else
        print_test "Token验证" "FAIL" "HTTP $HTTP_CODE"
        return 1
    fi
}

# 主测试流程
main() {
    echo ""
    echo "============================================================"
    echo "  🔐 用户登录和注册模块综合测试"
    echo "============================================================"
    echo "测试时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "API地址: $BASE_URL"
    echo "数据库: $DB_PATH"
    
    # 检查服务器
    if ! curl -s -f "http://localhost:8000/docs" > /dev/null 2>&1; then
        echo -e "${RED}❌ 错误: 无法连接到服务器 http://localhost:8000${NC}"
        echo "请确保后端服务已启动: cd backend && ./run.sh"
        exit 1
    fi
    echo -e "${GREEN}✅ 服务器连接正常${NC}"
    
    # 执行测试
    test_admin_login
    test_user_register
    TEST_USERNAME=$(cat /tmp/test_username.txt 2>/dev/null)
    TEST_EMAIL=$(cat /tmp/test_email.txt 2>/dev/null)
    test_new_user_login "$TEST_USERNAME"
    test_wrong_password
    test_nonexistent_user
    test_duplicate_username
    
    # 数据库验证
    if [ -n "$TEST_USERNAME" ]; then
        check_database "$TEST_USERNAME" "$TEST_EMAIL"
    fi
    
    # Token验证
    test_token_validation
    
    # 打印总结
    print_section "测试总结"
    TOTAL=$((PASSED + FAILED))
    PASS_RATE=$(awk "BEGIN {printf \"%.1f\", ($PASSED/$TOTAL)*100}")
    
    echo "总测试数: $TOTAL"
    echo -e "${GREEN}通过: $PASSED ✅${NC}"
    echo -e "${RED}失败: $FAILED ❌${NC}"
    echo "通过率: ${PASS_RATE}%"
    
    if [ $FAILED -eq 0 ]; then
        echo ""
        echo -e "${GREEN}🎉 所有测试通过！${NC}"
        exit 0
    else
        echo ""
        echo -e "${RED}⚠️  有 $FAILED 个测试失败${NC}"
        exit 1
    fi
}

# 运行主函数
main

