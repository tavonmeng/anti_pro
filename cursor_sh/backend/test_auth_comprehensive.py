#!/usr/bin/env python3
"""
用户登录和注册模块综合测试脚本
测试完成后会检查数据库确认注册结果
"""

import requests
import json
import sys
import sqlite3
from datetime import datetime

BASE_URL = "http://localhost:8000/api"
DB_PATH = "./app.db"

# 测试结果记录
test_results = []

def print_section(title):
    """打印测试章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_test(name, status, details=""):
    """打印测试结果"""
    status_symbol = "✅" if status else "❌"
    print(f"{status_symbol} {name}")
    if details:
        print(f"   {details}")
    test_results.append({
        "name": name,
        "status": "PASS" if status else "FAIL",
        "details": details
    })

def test_admin_login():
    """测试管理员登录"""
    print_section("测试用例 1: 管理员登录")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={
                "username": "admin",
                "password": "123456",
                "role": "admin",
                "captcha": "1234"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200 and "data" in data:
                token = data["data"].get("token")
                user = data["data"].get("user")
                if token and user:
                    print_test(
                        "管理员登录",
                        True,
                        f"Token: {token[:50]}... | 用户: {user.get('username')} ({user.get('role')})"
                    )
                    return token
                else:
                    print_test("管理员登录", False, "响应中缺少 token 或 user 信息")
                    return None
            else:
                print_test("管理员登录", False, f"响应格式错误: {data}")
                return None
        else:
            print_test("管理员登录", False, f"HTTP {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print_test("管理员登录", False, f"请求异常: {str(e)}")
        return None

def test_user_register():
    """测试用户注册"""
    print_section("测试用例 2: 用户注册")
    
    # 生成唯一的用户名
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_username = f"testuser_{timestamp}"
    test_email = f"{test_username}@test.com"
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "username": test_username,
                "email": test_email,
                "password": "123456",
                "role": "user"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                print_test(
                    "用户注册",
                    True,
                    f"用户名: {test_username} | 邮箱: {test_email}"
                )
                return test_username, test_email
            else:
                print_test("用户注册", False, f"响应错误: {data}")
                return None, None
        else:
            print_test("用户注册", False, f"HTTP {response.status_code}: {response.text}")
            return None, None
    except Exception as e:
        print_test("用户注册", False, f"请求异常: {str(e)}")
        return None, None

def test_new_user_login(username):
    """测试新注册用户登录"""
    print_section("测试用例 3: 新注册用户登录")
    
    if not username:
        print_test("新用户登录", False, "跳过：用户未成功注册")
        return None
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={
                "username": username,
                "password": "123456",
                "role": "user",
                "captcha": "1234"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200 and "data" in data:
                token = data["data"].get("token")
                user = data["data"].get("user")
                if token and user:
                    print_test(
                        "新用户登录",
                        True,
                        f"Token: {token[:50]}... | 用户: {user.get('username')}"
                    )
                    return token
                else:
                    print_test("新用户登录", False, "响应中缺少 token 或 user 信息")
                    return None
            else:
                print_test("新用户登录", False, f"响应格式错误: {data}")
                return None
        else:
            print_test("新用户登录", False, f"HTTP {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print_test("新用户登录", False, f"请求异常: {str(e)}")
        return None

def test_wrong_password():
    """测试错误密码"""
    print_section("测试用例 4: 错误密码（应该失败）")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={
                "username": "admin",
                "password": "wrongpassword",
                "role": "admin",
                "captcha": "1234"
            },
            timeout=5
        )
        
        if response.status_code == 401:
            print_test("错误密码测试", True, "正确返回 401 未授权错误")
            return True
        else:
            print_test("错误密码测试", False, f"应该返回 401，实际返回 {response.status_code}")
            return False
    except Exception as e:
        print_test("错误密码测试", False, f"请求异常: {str(e)}")
        return False

def test_nonexistent_user():
    """测试不存在用户"""
    print_section("测试用例 5: 不存在用户（应该失败）")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={
                "username": "nonexistent_user_12345",
                "password": "123456",
                "role": "user",
                "captcha": "1234"
            },
            timeout=5
        )
        
        if response.status_code == 401:
            print_test("不存在用户测试", True, "正确返回 401 未授权错误")
            return True
        else:
            print_test("不存在用户测试", False, f"应该返回 401，实际返回 {response.status_code}")
            return False
    except Exception as e:
        print_test("不存在用户测试", False, f"请求异常: {str(e)}")
        return False

def test_duplicate_username():
    """测试重复用户名注册"""
    print_section("测试用例 6: 重复用户名注册（应该失败）")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "username": "admin",
                "email": "admin2@test.com",
                "password": "123456",
                "role": "user"
            },
            timeout=5
        )
        
        if response.status_code == 409:
            print_test("重复用户名测试", True, "正确返回 409 冲突错误")
            return True
        else:
            print_test("重复用户名测试", False, f"应该返回 409，实际返回 {response.status_code}")
            return False
    except Exception as e:
        print_test("重复用户名测试", False, f"请求异常: {str(e)}")
        return False

def check_database(username, email):
    """检查数据库确认用户已注册"""
    print_section("数据库验证: 检查注册用户")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 查询用户
        cursor.execute(
            "SELECT id, username, email, role, is_active, created_at FROM users WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()
        
        if user:
            user_id, db_username, db_email, role, is_active, created_at = user
            print_test(
                "数据库验证",
                True,
                f"用户ID: {user_id} | 用户名: {db_username} | 邮箱: {db_email} | 角色: {role} | 状态: {'激活' if is_active else '禁用'} | 创建时间: {created_at}"
            )
            
            # 验证信息是否匹配
            if db_username == username and db_email == email:
                print_test("数据一致性验证", True, "数据库中的用户名和邮箱与注册信息一致")
            else:
                print_test("数据一致性验证", False, f"数据不匹配: 期望({username}, {email}), 实际({db_username}, {db_email})")
            
            conn.close()
            return True
        else:
            print_test("数据库验证", False, f"数据库中未找到用户: {username}")
            conn.close()
            return False
            
    except Exception as e:
        print_test("数据库验证", False, f"数据库查询异常: {str(e)}")
        return False

def test_token_validation(token):
    """测试Token有效性"""
    print_section("测试用例 7: Token验证（访问受保护接口）")
    
    if not token:
        print_test("Token验证", False, "跳过：未获取到有效Token")
        return False
    
    try:
        response = requests.get(
            f"{BASE_URL}/orders",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        
        if response.status_code == 200:
            print_test("Token验证", True, "Token有效，可以访问受保护接口")
            return True
        elif response.status_code == 401:
            print_test("Token验证", False, "Token无效或已过期")
            return False
        else:
            print_test("Token验证", False, f"HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_test("Token验证", False, f"请求异常: {str(e)}")
        return False

def print_summary():
    """打印测试总结"""
    print_section("测试总结")
    
    total = len(test_results)
    passed = sum(1 for r in test_results if r["status"] == "PASS")
    failed = total - passed
    
    print(f"总测试数: {total}")
    print(f"通过: {passed} ✅")
    print(f"失败: {failed} ❌")
    print(f"通过率: {passed/total*100:.1f}%")
    
    if failed > 0:
        print("\n失败的测试:")
        for r in test_results:
            if r["status"] == "FAIL":
                print(f"  ❌ {r['name']}: {r['details']}")
    
    return passed == total

def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("  🔐 用户登录和注册模块综合测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API地址: {BASE_URL}")
    print(f"数据库: {DB_PATH}")
    
    # 测试流程
    admin_token = test_admin_login()
    test_username, test_email = test_user_register()
    new_user_token = test_new_user_login(test_username)
    test_wrong_password()
    test_nonexistent_user()
    test_duplicate_username()
    
    # 数据库验证
    if test_username:
        check_database(test_username, test_email)
    
    # Token验证
    if admin_token:
        test_token_validation(admin_token)
    
    # 打印总结
    all_passed = print_summary()
    
    # 返回退出码
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()

