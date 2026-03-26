"""
用户管理接口测试模块。

测试覆盖：
1. 正常路径：创建用户、获取用户列表、获取单个用户、更新用户、删除用户
2. 异常路径：重复用户名/邮箱、用户不存在、权限不足、数据验证错误
3. 响应体结构校验
"""

import pytest
from fastapi import status

from ..schemas.users import UserResponse


class TestUserEndpoints:
    """用户管理接口测试类"""

    def test_create_user_success(self, client, user_token_headers):
        """测试创建用户 - 正常路径"""
        # 准备测试数据
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "newpass123",
            "disabled": False
        }

        # 发送创建用户请求
        response = client.post(
            "/users/",
            json=user_data,
            headers=user_token_headers
        )

        # 验证响应状态码
        assert response.status_code == status.HTTP_201_CREATED, f"创建用户失败: {response.text}"

        # 验证响应结构
        response_data = response.json()
        assert "id" in response_data, "响应应包含id字段"
        assert response_data["username"] == "newuser", "用户名不匹配"
        assert response_data["email"] == "newuser@example.com", "邮箱不匹配"
        assert response_data["full_name"] == "New User", "全名不匹配"
        assert response_data["disabled"] == False, "disabled状态不匹配"
        assert "password_hash" not in response_data, "响应不应包含密码哈希"
        assert "password" not in response_data, "响应不应包含密码"

        # 使用Pydantic模型验证响应数据结构
        user = UserResponse(**response_data)
        assert user.id is not None

    def test_create_user_duplicate_username(self, client, user_token_headers, test_user):
        """测试创建用户 - 用户名已存在 - 异常路径"""
        user_data = {
            "username": "testuser",  # 已存在的用户名
            "email": "another@example.com",
            "full_name": "Another User",
            "password": "pass1234",
            "disabled": False
        }

        response = client.post(
            "/users/",
            json=user_data,
            headers=user_token_headers
        )

        # 验证返回400错误
        assert response.status_code == status.HTTP_400_BAD_REQUEST, "重复用户名应返回400"
        assert response.json()["detail"] == "用户名已存在", "错误信息不正确"

    def test_create_user_duplicate_email(self, client, user_token_headers, test_user):
        """测试创建用户 - 邮箱已存在 - 异常路径"""
        user_data = {
            "username": "anotheruser",
            "email": "test@example.com",  # 已存在的邮箱
            "full_name": "Another User",
            "password": "pass1234",
            "disabled": False
        }

        response = client.post(
            "/users/",
            json=user_data,
            headers=user_token_headers
        )

        # 验证返回400错误
        assert response.status_code == status.HTTP_400_BAD_REQUEST, "重复邮箱应返回400"
        assert response.json()["detail"] == "邮箱已存在", "错误信息不正确"

    def test_create_user_invalid_username(self, client, user_token_headers):
        """测试创建用户 - 用户名格式错误 - 异常路径"""
        # 用户名包含特殊字符
        user_data = {
            "username": "invalid@user",
            "email": "valid@example.com",
            "full_name": "Valid Name",
            "password": "pass1234",
            "disabled": False
        }

        response = client.post(
            "/users/",
            json=user_data,
            headers=user_token_headers
        )

        # 验证返回422验证错误
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, "无效用户名应返回422"

    def test_create_user_short_password(self, client, user_token_headers):
        """测试创建用户 - 密码过短 - 异常路径"""
        user_data = {
            "username": "validuser",
            "email": "valid@example.com",
            "full_name": "Valid Name",
            "password": "12345",  # 少于6个字符
            "disabled": False
        }

        response = client.post(
            "/users/",
            json=user_data,
            headers=user_token_headers
        )

        # 验证返回422验证错误
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, "短密码应返回422"

    def test_get_users_list(self, client, user_token_headers, test_session):
        """测试获取用户列表 - 正常路径"""
        # 先创建几个测试用户
        from ..core.models import User
        from ..core.security import get_password_hash

        for i in range(3):
            user = User(
                username=f"user{i}",
                email=f"user{i}@example.com",
                full_name=f"User {i}",
                password_hash=get_password_hash("pass1234"),
                disabled=False,
            )
            test_session.add(user)
        test_session.commit()

        # 发送获取列表请求
        response = client.get("/users/", headers=user_token_headers)

        # 验证响应
        assert response.status_code == status.HTTP_200_OK, "获取用户列表失败"
        response_data = response.json()
        assert isinstance(response_data, list), "响应应为列表类型"
        assert len(response_data) >= 3, "用户列表数量不正确"

        # 验证每个用户的结构
        for user_data in response_data:
            user = UserResponse(**user_data)
            assert user.id is not None
            assert "password_hash" not in user_data

    def test_get_users_pagination(self, client, user_token_headers, test_session):
        """测试获取用户列表 - 分页功能 - 正常路径"""
        # 创建多个测试用户
        from ..core.models import User
        from ..core.security import get_password_hash

        # 清除现有用户（除了test_user）
        from sqlmodel import select
        results = test_session.exec(select(User).where(User.username != "testuser")).all()
        for user in results:
            test_session.delete(user)
        test_session.commit()

        for i in range(15):
            user = User(
                username=f"pageuser{i:02d}",
                email=f"pageuser{i:02d}@example.com",
                full_name=f"Page User {i}",
                password_hash=get_password_hash("pass1234"),
                disabled=False,
            )
            test_session.add(user)
        test_session.commit()

        # 测试第一页
        response = client.get("/users/?offset=0&limit=5", headers=user_token_headers)
        assert response.status_code == status.HTTP_200_OK
        page1 = response.json()
        assert len(page1) == 5, "第一页应有5个用户"

        # 测试第二页
        response = client.get("/users/?offset=5&limit=5", headers=user_token_headers)
        assert response.status_code == status.HTTP_200_OK
        page2 = response.json()
        assert len(page2) == 5, "第二页应有5个用户"

        # 验证两页数据不重复
        page1_ids = {u["id"] for u in page1}
        page2_ids = {u["id"] for u in page2}
        assert page1_ids.isdisjoint(page2_ids), "分页数据不应重复"

    def test_get_single_user(self, client, user_token_headers, test_user):
        """测试获取单个用户 - 正常路径"""
        response = client.get(f"/users/{test_user.id}", headers=user_token_headers)

        assert response.status_code == status.HTTP_200_OK, "获取单个用户失败"
        response_data = response.json()
        assert response_data["id"] == test_user.id, "用户ID不匹配"
        assert response_data["username"] == test_user.username, "用户名不匹配"
        assert response_data["email"] == test_user.email, "邮箱不匹配"

        # 验证结构
        user = UserResponse(**response_data)
        assert user.id == test_user.id

    def test_get_user_not_found(self, client, user_token_headers):
        """测试获取单个用户 - 用户不存在 - 异常路径"""
        response = client.get("/users/99999", headers=user_token_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND, "不存在的用户应返回404"
        assert response.json()["detail"] == "用户不存在", "错误信息不正确"

    def test_get_current_user_info(self, client, user_token_headers, test_user):
        """测试获取当前用户信息 - 正常路径"""
        response = client.get("/users/me", headers=user_token_headers)

        assert response.status_code == status.HTTP_200_OK, "获取当前用户信息失败"
        response_data = response.json()
        assert response_data["username"] == test_user.username, "用户名不匹配"
        assert response_data["email"] == test_user.email, "邮箱不匹配"

    def test_update_user_success(self, client, user_token_headers, test_session):
        """测试更新用户 - 正常路径"""
        # 先创建一个用户用于更新
        from ..core.models import User
        from ..core.security import get_password_hash

        user = User(
            username="toupdate",
            email="toupdate@example.com",
            full_name="To Update",
            password_hash=get_password_hash("pass1234"),
            disabled=False,
        )
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)

        # 更新数据
        update_data = {
            "username": "updateduser",
            "email": "updated@example.com",
            "full_name": "Updated User",
            "password": "newpass456",
            "disabled": True
        }

        response = client.put(
            f"/users/{user.id}",
            json=update_data,
            headers=user_token_headers
        )

        assert response.status_code == status.HTTP_200_OK, "更新用户失败"
        response_data = response.json()
        assert response_data["username"] == "updateduser", "用户名未更新"
        assert response_data["email"] == "updated@example.com", "邮箱未更新"
        assert response_data["disabled"] == True, "disabled状态未更新"

    def test_update_user_not_found(self, client, user_token_headers):
        """测试更新用户 - 用户不存在 - 异常路径"""
        update_data = {
            "username": "updateduser",
            "email": "updated@example.com",
            "full_name": "Updated User",
            "password": "newpass456",
            "disabled": False
        }

        response = client.put(
            "/users/99999",
            json=update_data,
            headers=user_token_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND, "更新不存在的用户应返回404"

    def test_partial_update_user_success(self, client, user_token_headers, test_session):
        """测试部分更新用户 - 正常路径"""
        # 创建用户
        from ..core.models import User
        from ..core.security import get_password_hash

        user = User(
            username="partialuser",
            email="partial@example.com",
            full_name="Partial User",
            password_hash=get_password_hash("pass1234"),
            disabled=False,
        )
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)

        # 只更新邮箱
        update_data = {
            "email": "newemail@example.com"
        }

        response = client.patch(
            f"/users/{user.id}",
            json=update_data,
            headers=user_token_headers
        )

        assert response.status_code == status.HTTP_200_OK, "部分更新用户失败"
        response_data = response.json()
        assert response_data["email"] == "newemail@example.com", "邮箱未更新"
        assert response_data["username"] == "partialuser", "用户名不应改变"

    def test_delete_user_success(self, client, user_token_headers, test_session):
        """测试删除用户 - 正常路径"""
        # 创建用户
        from ..core.models import User
        from ..core.security import get_password_hash

        user = User(
            username="todelete",
            email="todelete@example.com",
            full_name="To Delete",
            password_hash=get_password_hash("pass1234"),
            disabled=False,
        )
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)
        user_id = user.id

        # 删除用户
        response = client.delete(f"/users/{user_id}", headers=user_token_headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT, "删除用户失败"

        # 验证用户已删除
        deleted_user = test_session.get(User, user_id)
        assert deleted_user is None, "用户未被删除"

    def test_delete_user_not_found(self, client, user_token_headers):
        """测试删除用户 - 用户不存在 - 异常路径"""
        response = client.delete("/users/99999", headers=user_token_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND, "删除不存在的用户应返回404"

    def test_unauthorized_access(self, unauthenticated_client):
        """测试未授权访问 - 异常路径"""
        # 尝试在未登录的情况下访问需要认证的接口
        response = unauthenticated_client.get("/users/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED, "未授权访问应返回401"

        response = unauthenticated_client.get("/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED, "未授权访问应返回401"

    def test_create_user_invalid_email(self, client, user_token_headers):
        """测试创建用户 - 邮箱格式无效 - 异常路径"""
        user_data = {
            "username": "validuser",
            "email": "invalid-email",  # 无效邮箱格式
            "full_name": "Valid Name",
            "password": "pass1234",
            "disabled": False
        }

        response = client.post(
            "/users/",
            json=user_data,
            headers=user_token_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, "无效邮箱应返回422"
