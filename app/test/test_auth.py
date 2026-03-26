"""认证接口测试模块。

测试登录、令牌获取等认证相关接口，包括：
- 正常登录流程
- 异常登录场景（错误密码、用户不存在、禁用用户）
- 响应数据结构校验
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from ..core.models import User
from ..core.security import get_password_hash


class TestAuthLogin:
    """测试登录接口 (/auth/login)。"""

    def test_login_success(self, client: TestClient, db_session: Session, test_user_data: dict):
        """测试正常登录成功。

        验证：
        - 返回200状态码
        - 响应包含access_token和token_type字段
        - token_type为"bearer"
        - access_token为非空字符串
        """
        # 准备：在数据库中创建测试用户
        user = User(
            username=test_user_data["username"],
            email=test_user_data["email"],
            full_name=test_user_data["full_name"],
            password_hash=get_password_hash(test_user_data["password"]),
            disabled=False,
        )
        db_session.add(user)
        db_session.commit()

        # 执行：发送登录请求
        response = client.post(
            "/auth/login",
            data={
                "username": test_user_data["username"],
                "password": test_user_data["password"],
            },
        )

        # 验证：检查响应状态码和数据结构
        assert response.status_code == 200, f"登录失败: {response.text}"
        data = response.json()

        # 验证响应体结构
        assert "access_token" in data, "响应缺少access_token字段"
        assert "token_type" in data, "响应缺少token_type字段"
        assert isinstance(data["access_token"], str), "access_token应为字符串"
        assert len(data["access_token"]) > 0, "access_token不应为空"
        assert data["token_type"] == "bearer", "token_type应为bearer"

    def test_login_wrong_password(self, client: TestClient, db_session: Session, test_user_data: dict):
        """测试使用错误密码登录失败。

        验证：
        - 返回401状态码
        - 响应包含错误详情
        """
        # 准备：创建测试用户
        user = User(
            username=test_user_data["username"],
            email=test_user_data["email"],
            full_name=test_user_data["full_name"],
            password_hash=get_password_hash(test_user_data["password"]),
            disabled=False,
        )
        db_session.add(user)
        db_session.commit()

        # 执行：使用错误密码登录
        response = client.post(
            "/auth/login",
            data={
                "username": test_user_data["username"],
                "password": "wrongpassword",
            },
        )

        # 验证：检查401错误响应
        assert response.status_code == 401, f"预期401，实际{response.status_code}"
        data = response.json()
        assert "detail" in data, "错误响应应包含detail字段"
        assert "用户名或密码错误" in data["detail"], "错误信息应提示用户名或密码错误"

    def test_login_nonexistent_user(self, client: TestClient, test_user_data: dict):
        """测试使用不存在的用户名登录失败。

        验证：
        - 返回401状态码
        - 响应包含错误详情
        """
        # 执行：使用不存在的用户登录
        response = client.post(
            "/auth/login",
            data={
                "username": "nonexistentuser",
                "password": "somepassword",
            },
        )

        # 验证：检查401错误响应
        assert response.status_code == 401, f"预期401，实际{response.status_code}"
        data = response.json()
        assert "detail" in data, "错误响应应包含detail字段"

    def test_login_disabled_user(self, client: TestClient, db_session: Session, test_user_disabled_data: dict):
        """测试被禁用的用户登录失败。

        验证：
        - 返回400状态码
        - 响应提示账户已被禁用
        """
        # 准备：创建被禁用的用户
        user = User(
            username=test_user_disabled_data["username"],
            email=test_user_disabled_data["email"],
            full_name=test_user_disabled_data["full_name"],
            password_hash=get_password_hash(test_user_disabled_data["password"]),
            disabled=True,
        )
        db_session.add(user)
        db_session.commit()

        # 执行：尝试登录被禁用的账户
        response = client.post(
            "/auth/login",
            data={
                "username": test_user_disabled_data["username"],
                "password": test_user_disabled_data["password"],
            },
        )

        # 验证：检查400错误响应
        assert response.status_code == 400, f"预期400，实际{response.status_code}"
        data = response.json()
        assert "detail" in data, "错误响应应包含detail字段"
        assert "禁用" in data["detail"], "错误信息应提示账户被禁用"

    def test_login_missing_username(self, client: TestClient):
        """测试缺少用户名参数的登录请求。

        验证：
        - 返回422验证错误
        """
        # 执行：发送缺少用户名的请求
        response = client.post(
            "/auth/login",
            data={"password": "somepassword"},
        )

        # 验证：检查422验证错误
        assert response.status_code == 422, f"预期422，实际{response.status_code}"

    def test_login_missing_password(self, client: TestClient):
        """测试缺少密码参数的登录请求。

        验证：
        - 返回422验证错误
        """
        # 执行：发送缺少密码的请求
        response = client.post(
            "/auth/login",
            data={"username": "testuser"},
        )

        # 验证：检查422验证错误
        assert response.status_code == 422, f"预期422，实际{response.status_code}"


class TestAuthToken:
    """测试令牌接口 (/auth/token)。"""

    def test_token_endpoint_success(self, client: TestClient, db_session: Session, test_user_data: dict):
        """测试通过/token端点获取令牌成功。

        /token端点与/login功能相同，用于OAuth2标准兼容。

        验证：
        - 返回200状态码
        - 响应包含有效的访问令牌
        """
        # 准备：创建测试用户
        user = User(
            username=test_user_data["username"],
            email=test_user_data["email"],
            full_name=test_user_data["full_name"],
            password_hash=get_password_hash(test_user_data["password"]),
            disabled=False,
        )
        db_session.add(user)
        db_session.commit()

        # 执行：请求令牌
        response = client.post(
            "/auth/token",
            data={
                "username": test_user_data["username"],
                "password": test_user_data["password"],
            },
        )

        # 验证：检查成功响应
        assert response.status_code == 200, f"获取令牌失败: {response.text}"
        data = response.json()
        assert "access_token" in data, "响应应包含access_token"
        assert data["token_type"] == "bearer", "token_type应为bearer"

    def test_token_endpoint_invalid_credentials(self, client: TestClient):
        """测试使用无效凭据获取令牌失败。

        验证：
        - 返回401状态码
        """
        # 执行：使用无效凭据
        response = client.post(
            "/auth/token",
            data={
                "username": "invalid",
                "password": "invalid",
            },
        )

        # 验证：检查401错误
        assert response.status_code == 401, f"预期401，实际{response.status_code}"


class TestAuthResponseStructure:
    """测试认证响应的数据结构。"""

    def test_token_response_structure(self, client: TestClient, db_session: Session, test_user_data: dict):
        """测试令牌响应的数据结构完整性。

        验证响应体包含所有必需字段且类型正确。
        """
        # 准备：创建测试用户
        user = User(
            username=test_user_data["username"],
            email=test_user_data["email"],
            full_name=test_user_data["full_name"],
            password_hash=get_password_hash(test_user_data["password"]),
            disabled=False,
        )
        db_session.add(user)
        db_session.commit()

        # 执行：登录获取令牌
        response = client.post(
            "/auth/login",
            data={
                "username": test_user_data["username"],
                "password": test_user_data["password"],
            },
        )

        # 验证：解析并验证响应结构
        data = response.json()

        # 验证字段存在性
        required_fields = ["access_token", "token_type"]
        for field in required_fields:
            assert field in data, f"响应缺少必需字段: {field}"

        # 验证字段类型
        assert isinstance(data["access_token"], str), "access_token应为字符串"
        assert isinstance(data["token_type"], str), "token_type应为字符串"

        # 验证字段值
        assert len(data["access_token"]) > 0, "access_token不应为空"
        assert data["token_type"].lower() == "bearer", "token_type应为'bearer'"

    def test_error_response_structure(self, client: TestClient):
        """测试错误响应的数据结构。

        验证错误响应包含标准的detail字段。
        """
        # 执行：触发错误
        response = client.post(
            "/auth/login",
            data={"username": "nonexistent", "password": "wrong"},
        )

        # 验证：检查错误响应结构
        assert response.status_code == 401
        data = response.json()

        # 验证错误响应包含detail字段
        assert "detail" in data, "错误响应应包含detail字段"
        assert isinstance(data["detail"], str), "detail应为字符串"


class TestAuthEdgeCases:
    """测试认证接口的边界情况。"""

    def test_login_with_empty_username(self, client: TestClient):
        """测试使用空用户名登录。

        验证：
        - 返回422验证错误
        """
        response = client.post(
            "/auth/login",
            data={"username": "", "password": "password"},
        )
        # OAuth2表单验证会拒绝空值
        assert response.status_code == 422

    def test_login_with_empty_password(self, client: TestClient):
        """测试使用空密码登录。

        验证：
        - 返回422验证错误
        """
        response = client.post(
            "/auth/login",
            data={"username": "user", "password": ""},
        )
        # OAuth2表单验证会拒绝空值
        assert response.status_code == 422

    def test_login_with_special_characters_in_username(self, client: TestClient):
        """测试用户名中包含特殊字符。

        验证：
        - 对于不存在的特殊字符用户名返回401
        """
        response = client.post(
            "/auth/login",
            data={"username": "user@#$%", "password": "password"},
        )
        # 用户不存在，返回401
        assert response.status_code == 401

    @pytest.mark.parametrize("username,password", [
        ("user", "short"),
        ("user", "a" * 200),  # 超长密码
        ("user", "密码中文测试"),  # 中文密码
    ])
    def test_login_with_various_passwords(self, client: TestClient, username: str, password: str):
        """测试各种密码格式的登录尝试。

        参数化测试用例，验证不同密码格式的处理。
        """
        response = client.post(
            "/auth/login",
            data={"username": username, "password": password},
        )
        # 用户不存在，都应返回401
        assert response.status_code == 401
