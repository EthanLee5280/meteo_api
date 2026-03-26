"""认证接口测试模块。

测试用户登录、令牌验证等认证相关功能。
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import status

from app.core.security import create_access_token
from app.core.models import User
from app.test.conftest import assert_response_structure


class TestLogin:
    """登录接口测试类。

    测试用户登录的各种场景，包括成功登录和失败情况。
    """

    def test_login_success(self, client: TestClient, test_user: User):
        """测试正常登录成功。

        使用正确的用户名和密码登录，验证返回的令牌格式正确。
        OAuth2密码流程要求使用form-data格式提交。

        Args:
            client: 测试客户端
            test_user: 测试用户
        """
        response = client.post(
            "/auth/login",
            data={
                "username": test_user.username,
                "password": "testpassword123",
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert_response_structure(data, ["access_token", "token_type"])
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """测试密码错误登录失败。

        使用错误密码登录，验证返回401错误。

        Args:
            client: 测试客户端
            test_user: 测试用户
        """
        response = client.post(
            "/auth/login",
            data={
                "username": test_user.username,
                "password": "wrongpassword",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "用户名或密码错误"

    def test_login_nonexistent_user(self, client: TestClient):
        """测试不存在的用户登录失败。

        使用不存在的用户名登录，验证返回401错误。

        Args:
            client: 测试客户端
        """
        response = client.post(
            "/auth/login",
            data={
                "username": "nonexistent",
                "password": "anypassword",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "用户名或密码错误"

    def test_login_disabled_user(self, client: TestClient, disabled_user: User):
        """测试被禁用用户登录失败。

        使用被禁用的账户登录，验证返回400错误。

        Args:
            client: 测试客户端
            disabled_user: 被禁用的测试用户
        """
        response = client.post(
            "/auth/login",
            data={
                "username": disabled_user.username,
                "password": "testpassword123",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "用户账户已被禁用"

    def test_login_missing_username(self, client: TestClient):
        """测试缺少用户名登录失败。

        不提供用户名，验证返回422验证错误。

        Args:
            client: 测试客户端
        """
        response = client.post(
            "/auth/login",
            data={
                "password": "testpassword123",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_missing_password(self, client: TestClient):
        """测试缺少密码登录失败。

        不提供密码，验证返回422验证错误。

        Args:
            client: 测试客户端
        """
        response = client.post(
            "/auth/login",
            data={
                "username": "testuser",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestToken:
    """令牌接口测试类。

    测试令牌端点（与/login功能相同，兼容OAuth2标准命名）。
    """

    def test_token_endpoint_success(self, client: TestClient, test_user: User):
        """测试/token端点正常工作。

        验证/token端点与/login功能一致。

        Args:
            client: 测试客户端
            test_user: 测试用户
        """
        response = client.post(
            "/auth/token",
            data={
                "username": test_user.username,
                "password": "testpassword123",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


class TestAuthenticationFlow:
    """认证流程集成测试类。

    测试完整的认证流程，包括登录后使用令牌访问受保护资源。
    """

    def test_access_protected_route_without_token(self, client: TestClient):
        """测试无令牌访问受保护路由。

        不提供认证令牌访问需要认证的接口，验证返回401错误。

        Args:
            client: 测试客户端
        """
        response = client.get("/users/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Not authenticated"

    def test_access_protected_route_with_invalid_token(self, client: TestClient):
        """测试无效令牌访问受保护路由。

        使用无效的令牌访问需要认证的接口，验证返回401错误。

        Args:
            client: 测试客户端
        """
        response = client.get(
            "/users/me",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_protected_route_with_valid_token(
        self, client: TestClient, auth_headers: dict
    ):
        """测试有效令牌访问受保护路由。

        使用有效的令牌访问需要认证的接口，验证成功返回数据。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        response = client.get("/users/me", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testuser"

    def test_access_protected_route_with_expired_token(
        self, client: TestClient, test_user: User
    ):
        """测试过期令牌访问受保护路由。

        使用过期的令牌访问需要认证的接口，验证返回401错误。
        注意：这里通过模拟过期令牌来测试，实际过期需要等待时间。

        Args:
            client: 测试客户端
            test_user: 测试用户
        """
        from datetime import timedelta

        expired_token = create_access_token(
            data={"sub": test_user.username},
            expires_delta=timedelta(seconds=-1),
        )

        response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "令牌已过期"

    def test_access_protected_route_with_malformed_auth_header(
        self, client: TestClient
    ):
        """测试格式错误的认证头。

        使用格式错误的Authorization头，验证返回401错误。

        Args:
            client: 测试客户端
        """
        response = client.get(
            "/users/me",
            headers={"Authorization": "InvalidScheme token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_protected_route_by_disabled_user(
        self, client: TestClient, disabled_user: User
    ):
        """测试被禁用用户访问受保护路由。

        被禁用用户即使有有效令牌也无法访问受保护资源。

        Args:
            client: 测试客户端
            disabled_user: 被禁用的测试用户
        """
        token = create_access_token(data={"sub": disabled_user.username})

        response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "用户账户已被禁用"
