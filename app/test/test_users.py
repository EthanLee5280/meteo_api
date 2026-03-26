"""用户接口测试模块。

测试用户CRUD操作相关功能。
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlmodel import Session

from app.core.models import User
from app.core.security import get_password_hash
from app.test.conftest import assert_user_response_structure


class TestCreateUser:
    """创建用户接口测试类。

    测试用户创建的各种场景。
    """

    def test_create_user_success(self, client: TestClient, auth_headers: dict):
        """测试成功创建用户。

        使用有效的用户数据创建新用户，验证返回的用户信息正确。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "newpassword123",
            "disabled": False,
        }

        response = client.post("/users/", json=user_data, headers=auth_headers)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert_user_response_structure(data)
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["disabled"] is False
        assert "password" not in data

    def test_create_user_duplicate_username(
        self, client: TestClient, auth_headers: dict, test_user: User
    ):
        """测试创建重复用户名失败。

        尝试创建已存在的用户名，验证返回400错误。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            test_user: 已存在的测试用户
        """
        user_data = {
            "username": test_user.username,
            "email": "different@example.com",
            "full_name": "Different User",
            "password": "password123",
            "disabled": False,
        }

        response = client.post("/users/", json=user_data, headers=auth_headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "用户名已存在"

    def test_create_user_duplicate_email(
        self, client: TestClient, auth_headers: dict, test_user: User
    ):
        """测试创建重复邮箱失败。

        尝试创建已存在的邮箱，验证返回400错误。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            test_user: 已存在的测试用户
        """
        user_data = {
            "username": "differentuser",
            "email": test_user.email,
            "full_name": "Different User",
            "password": "password123",
            "disabled": False,
        }

        response = client.post("/users/", json=user_data, headers=auth_headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "邮箱已存在"

    def test_create_user_invalid_username_format(
        self, client: TestClient, auth_headers: dict
    ):
        """测试无效用户名格式。

        使用包含特殊字符的用户名，验证返回422验证错误。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        user_data = {
            "username": "invalid@user",
            "email": "valid@example.com",
            "full_name": "Invalid User",
            "password": "password123",
            "disabled": False,
        }

        response = client.post("/users/", json=user_data, headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_user_short_username(
        self, client: TestClient, auth_headers: dict
    ):
        """测试用户名过短。

        使用少于3个字符的用户名，验证返回422验证错误。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        user_data = {
            "username": "ab",
            "email": "valid@example.com",
            "full_name": "Short User",
            "password": "password123",
            "disabled": False,
        }

        response = client.post("/users/", json=user_data, headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_user_short_password(
        self, client: TestClient, auth_headers: dict
    ):
        """测试密码过短。

        使用少于6个字符的密码，验证返回422验证错误。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        user_data = {
            "username": "validuser",
            "email": "valid@example.com",
            "full_name": "Valid User",
            "password": "12345",
            "disabled": False,
        }

        response = client.post("/users/", json=user_data, headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_user_invalid_email(
        self, client: TestClient, auth_headers: dict
    ):
        """测试无效邮箱格式。

        使用无效的邮箱格式，验证返回422验证错误。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        user_data = {
            "username": "validuser",
            "email": "invalid-email",
            "full_name": "Valid User",
            "password": "password123",
            "disabled": False,
        }

        response = client.post("/users/", json=user_data, headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_user_without_auth(self, client: TestClient):
        """测试未认证创建用户。

        不提供认证令牌创建用户，验证返回401错误。

        Args:
            client: 测试客户端
        """
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "password123",
            "disabled": False,
        }

        response = client.post("/users/", json=user_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestReadUsers:
    """读取用户接口测试类。

    测试用户列表和单个用户查询功能。
    """

    def test_read_users_list(
        self, client: TestClient, auth_headers: dict, test_user: User
    ):
        """测试获取用户列表。

        验证返回的用户列表包含已创建的用户。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            test_user: 测试用户
        """
        response = client.get("/users/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        for user in data:
            assert_user_response_structure(user)

    def test_read_users_pagination(self, client: TestClient, auth_headers: dict):
        """测试用户列表分页。

        验证分页参数正确工作。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        response = client.get("/users/?offset=0&limit=10", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    def test_read_users_limit_exceeded(self, client: TestClient, auth_headers: dict):
        """测试分页限制。

        验证limit参数最大值为100。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        response = client.get("/users/?limit=200", headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_read_current_user(
        self, client: TestClient, auth_headers: dict, test_user: User
    ):
        """测试获取当前用户信息。

        验证返回当前登录用户的正确信息。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            test_user: 测试用户
        """
        response = client.get("/users/me", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert_user_response_structure(data)
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email

    def test_read_user_by_id(
        self, client: TestClient, auth_headers: dict, test_user: User
    ):
        """测试通过ID获取用户。

        验证返回指定ID的用户信息。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            test_user: 测试用户
        """
        response = client.get(f"/users/{test_user.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert_user_response_structure(data)
        assert data["id"] == test_user.id

    def test_read_nonexistent_user(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的用户。

        使用不存在的用户ID，验证返回404错误。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        response = client.get("/users/99999", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "用户不存在"


class TestUpdateUser:
    """更新用户接口测试类。

    测试用户更新功能（PUT和PATCH）。
    """

    def test_update_user_full(
        self, client: TestClient, auth_headers: dict, test_user: User
    ):
        """测试完全更新用户（PUT）。

        更新用户的所有字段，验证更新成功。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            test_user: 测试用户
        """
        update_data = {
            "username": "updateduser",
            "email": "updated@example.com",
            "full_name": "Updated User",
            "password": "newpassword123",
            "disabled": False,
        }

        response = client.put(
            f"/users/{test_user.id}", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "updateduser"
        assert data["email"] == "updated@example.com"
        assert data["full_name"] == "Updated User"

    def test_update_user_partial(
        self, client: TestClient, auth_headers: dict, test_user: User
    ):
        """测试部分更新用户（PATCH）。

        只更新部分字段，验证其他字段保持不变。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            test_user: 测试用户
        """
        original_email = test_user.email
        update_data = {
            "full_name": "Partially Updated",
        }

        response = client.patch(
            f"/users/{test_user.id}", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == "Partially Updated"
        assert data["email"] == original_email

    def test_update_nonexistent_user(self, client: TestClient, auth_headers: dict):
        """测试更新不存在的用户。

        使用不存在的用户ID，验证返回404错误。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        update_data = {
            "username": "updateduser",
            "email": "updated@example.com",
            "full_name": "Updated User",
            "password": "newpassword123",
            "disabled": False,
        }

        response = client.put("/users/99999", json=update_data, headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_user_duplicate_username(
        self, client: TestClient, auth_headers: dict, session: Session, test_user: User
    ):
        """测试更新用户名为已存在的用户名。

        尝试将用户名更新为其他用户已使用的用户名，验证返回400错误。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            session: 数据库会话
            test_user: 测试用户
        """
        other_user = User(
            username="otheruser",
            email="other@example.com",
            full_name="Other User",
            password_hash=get_password_hash("password123"),
        )
        session.add(other_user)
        session.commit()
        session.refresh(other_user)

        update_data = {
            "username": "otheruser",
            "email": test_user.email,
            "full_name": test_user.full_name,
            "password": "password123",
            "disabled": False,
        }

        response = client.put(
            f"/users/{test_user.id}", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "用户名已存在"


class TestDeleteUser:
    """删除用户接口测试类。

    测试用户删除功能。
    """

    def test_delete_user_success(
        self, client: TestClient, auth_headers: dict, session: Session
    ):
        """测试成功删除用户。

        创建一个用户后删除，验证删除成功。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            session: 数据库会话
        """
        user = User(
            username="tobedeleted",
            email="delete@example.com",
            full_name="To Be Deleted",
            password_hash=get_password_hash("password123"),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

        response = client.delete(f"/users/{user_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        deleted_user = session.get(User, user_id)
        assert deleted_user is None

    def test_delete_nonexistent_user(self, client: TestClient, auth_headers: dict):
        """测试删除不存在的用户。

        使用不存在的用户ID，验证返回404错误。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        response = client.delete("/users/99999", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
