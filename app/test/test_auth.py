"""
认证接口测试模块。

测试覆盖：
1. 正常路径：登录成功、获取token
2. 异常路径：用户名错误、密码错误、用户禁用、无效token等
3. 响应体结构校验
"""

import pytest
from fastapi import status

from ..schemas.auth import Token


class TestAuthEndpoints:
    """认证接口测试类"""

    def test_login_success(self, unauthenticated_client, test_user):
        """测试登录成功 - 正常路径"""
        # 准备测试数据
        login_data = {
            "username": "testuser",
            "password": "testpass123"
        }

        # 发送登录请求
        response = unauthenticated_client.post("/auth/login", data=login_data)

        # 验证响应状态码
        assert response.status_code == status.HTTP_200_OK, f"登录失败: {response.text}"

        # 验证响应结构
        response_data = response.json()
        assert "access_token" in response_data, "响应应包含access_token字段"
        assert "token_type" in response_data, "响应应包含token_type字段"
        assert response_data["token_type"] == "bearer", "token_type应为bearer"

        # 使用Pydantic模型验证响应数据结构
        token = Token(**response_data)
        assert token.access_token is not None, "access_token不应为空"

    def test_login_wrong_username(self, unauthenticated_client):
        """测试登录 - 用户名不存在 - 异常路径"""
        login_data = {
            "username": "nonexistentuser",
            "password": "testpass123"
        }

        response = unauthenticated_client.post("/auth/login", data=login_data)

        # 验证返回401未授权
        assert response.status_code == status.HTTP_401_UNAUTHORIZED, "用户名错误应返回401"
        assert "detail" in response.json(), "响应应包含错误详情"
        assert response.json()["detail"] == "用户名或密码错误", "错误信息不正确"

    def test_login_wrong_password(self, unauthenticated_client, test_user):
        """测试登录 - 密码错误 - 异常路径"""
        login_data = {
            "username": "testuser",
            "password": "wrongpassword"
        }

        response = unauthenticated_client.post("/auth/login", data=login_data)

        # 验证返回401未授权
        assert response.status_code == status.HTTP_401_UNAUTHORIZED, "密码错误应返回401"
        assert response.json()["detail"] == "用户名或密码错误", "错误信息不正确"

    def test_login_disabled_user(self, unauthenticated_client, test_session):
        """测试登录 - 用户被禁用 - 异常路径"""
        # 创建一个被禁用的用户
        from ..core.models import User
        from ..core.security import get_password_hash

        disabled_user = User(
            username="disableduser",
            email="disabled@example.com",
            full_name="Disabled User",
            password_hash=get_password_hash("testpass123"),
            disabled=True,
        )
        test_session.add(disabled_user)
        test_session.commit()

        login_data = {
            "username": "disableduser",
            "password": "testpass123"
        }

        response = unauthenticated_client.post("/auth/login", data=login_data)

        # 验证返回400错误
        assert response.status_code == status.HTTP_400_BAD_REQUEST, "禁用用户登录应返回400"
        assert response.json()["detail"] == "用户账户已被禁用", "错误信息不正确"

    def test_token_endpoint_success(self, unauthenticated_client, test_user):
        """测试获取token端点（OAuth2兼容端点） - 正常路径"""
        login_data = {
            "username": "testuser",
            "password": "testpass123"
        }

        response = unauthenticated_client.post("/auth/token", data=login_data)

        # 验证响应状态码和结构
        assert response.status_code == status.HTTP_200_OK, "获取token失败"
        response_data = response.json()
        assert "access_token" in response_data
        assert response_data["token_type"] == "bearer"

        # 使用Pydantic模型验证
        token = Token(**response_data)
        assert token.access_token is not None

    def test_login_empty_username(self, unauthenticated_client):
        """测试登录 - 用户名为空 - 异常路径"""
        login_data = {
            "username": "",
            "password": "testpass123"
        }

        response = unauthenticated_client.post("/auth/login", data=login_data)

        # 空用户名应该返回认证失败
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ], f"空用户名应返回401或422，实际返回: {response.status_code}"

    def test_login_empty_password(self, unauthenticated_client, test_user):
        """测试登录 - 密码为空 - 异常路径"""
        login_data = {
            "username": "testuser",
            "password": ""
        }

        response = unauthenticated_client.post("/auth/login", data=login_data)

        # 空密码可能返回422验证错误或401认证失败，取决于服务器实现
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ], f"空密码应返回401或422，实际返回: {response.status_code}"

    def test_login_missing_username_field(self, unauthenticated_client):
        """测试登录 - 缺少username字段 - 异常路径"""
        login_data = {
            "password": "testpass123"
        }

        response = unauthenticated_client.post("/auth/login", data=login_data)

        # 缺少字段应返回422
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, "缺少username字段应返回422"

    def test_login_missing_password_field(self, unauthenticated_client):
        """测试登录 - 缺少password字段 - 异常路径"""
        login_data = {
            "username": "testuser"
        }

        response = unauthenticated_client.post("/auth/login", data=login_data)

        # 缺少字段应返回422
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, "缺少password字段应返回422"
