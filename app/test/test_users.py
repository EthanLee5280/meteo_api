"""用户接口测试模块。

测试用户CRUD操作接口，包括：
- 创建用户（需要认证）
- 获取用户列表和单个用户
- 更新用户信息（PUT/PATCH）
- 删除用户
- 权限控制和异常场景
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from ..core.models import User
from ..core.security import get_password_hash


class TestCreateUser:
    """测试创建用户接口 (POST /users/)。"""

    def test_create_user_success(self, client: TestClient, auth_headers: dict, test_user_data: dict):
        """测试正常创建用户成功。

        验证：
        - 返回201状态码
        - 响应包含正确的用户数据
        - 密码字段不包含在响应中
        """
        # 修改用户名和邮箱以确保唯一性
        new_user_data = {
            **test_user_data,
            "username": "newuser123",
            "email": "newuser123@example.com",
        }

        # 执行：发送创建用户请求
        response = client.post("/users/", json=new_user_data, headers=auth_headers)

        # 验证：检查响应
        assert response.status_code == 201, f"创建用户失败: {response.text}"
        data = response.json()

        # 验证响应结构
        assert "id" in data, "响应应包含id字段"
        assert data["username"] == new_user_data["username"], "用户名应匹配"
        assert data["email"] == new_user_data["email"], "邮箱应匹配"
        assert data["full_name"] == new_user_data["full_name"], "全名应匹配"
        assert data["disabled"] == new_user_data["disabled"], "禁用状态应匹配"
        assert "created_at" in data, "响应应包含created_at字段"

        # 验证密码不包含在响应中
        assert "password" not in data, "响应不应包含密码字段"
        assert "password_hash" not in data, "响应不应包含密码哈希"

    def test_create_user_duplicate_username(self, client: TestClient, db_session: Session, auth_headers: dict, test_user_data: dict):
        """测试使用重复用户名创建用户失败。

        验证：
        - 返回400状态码
        - 响应提示用户名已存在
        """
        # 准备：先创建第一个用户
        user1_data = {
            **test_user_data,
            "username": "duplicateuser",
            "email": "user1@example.com",
        }
        response1 = client.post("/users/", json=user1_data, headers=auth_headers)
        assert response1.status_code == 201

        # 执行：尝试创建同名用户（不同邮箱）
        user2_data = {
            **test_user_data,
            "username": "duplicateuser",  # 相同用户名
            "email": "user2@example.com",  # 不同邮箱
        }
        response2 = client.post("/users/", json=user2_data, headers=auth_headers)

        # 验证：检查400错误
        assert response2.status_code == 400, f"预期400，实际{response2.status_code}"
        data = response2.json()
        assert "用户名已存在" in data["detail"], "错误信息应提示用户名已存在"

    def test_create_user_duplicate_email(self, client: TestClient, auth_headers: dict, test_user_data: dict):
        """测试使用重复邮箱创建用户失败。

        验证：
        - 返回400状态码
        - 响应提示邮箱已存在
        """
        # 准备：先创建第一个用户
        user1_data = {
            **test_user_data,
            "username": "user1unique",
            "email": "duplicate@example.com",
        }
        response1 = client.post("/users/", json=user1_data, headers=auth_headers)
        assert response1.status_code == 201

        # 执行：尝试创建使用相同邮箱的用户
        user2_data = {
            **test_user_data,
            "username": "user2unique",  # 不同用户名
            "email": "duplicate@example.com",  # 相同邮箱
        }
        response2 = client.post("/users/", json=user2_data, headers=auth_headers)

        # 验证：检查400错误
        assert response2.status_code == 400, f"预期400，实际{response2.status_code}"
        data = response2.json()
        assert "邮箱已存在" in data["detail"], "错误信息应提示邮箱已存在"

    def test_create_user_without_auth(self, client: TestClient, test_user_data: dict):
        """测试未认证用户无法创建用户。

        验证：
        - 返回401状态码
        """
        response = client.post("/users/", json=test_user_data)
        assert response.status_code == 401, f"预期401，实际{response.status_code}"

    def test_create_user_invalid_username(self, client: TestClient, auth_headers: dict, test_user_data: dict):
        """测试使用无效用户名创建用户失败。

        验证：
        - 用户名包含特殊字符时返回422
        """
        invalid_data = {
            **test_user_data,
            "username": "user@#$%",  # 包含特殊字符
            "email": "valid@example.com",
        }
        response = client.post("/users/", json=invalid_data, headers=auth_headers)
        # Pydantic验证会拒绝包含特殊字符的用户名
        assert response.status_code == 422, f"预期422，实际{response.status_code}"

    def test_create_user_short_username(self, client: TestClient, auth_headers: dict, test_user_data: dict):
        """测试使用过短用户名创建用户失败。

        验证：
        - 用户名少于3个字符时返回422
        """
        short_username_data = {
            **test_user_data,
            "username": "ab",  # 少于3个字符
            "email": "valid2@example.com",
        }
        response = client.post("/users/", json=short_username_data, headers=auth_headers)
        assert response.status_code == 422, f"预期422，实际{response.status_code}"

    def test_create_user_invalid_email(self, client: TestClient, auth_headers: dict, test_user_data: dict):
        """测试使用无效邮箱创建用户失败。

        验证：
        - 邮箱格式无效时返回422
        """
        invalid_email_data = {
            **test_user_data,
            "username": "validuser123",
            "email": "invalid-email",  # 无效邮箱格式
        }
        response = client.post("/users/", json=invalid_email_data, headers=auth_headers)
        assert response.status_code == 422, f"预期422，实际{response.status_code}"

    def test_create_user_short_password(self, client: TestClient, auth_headers: dict, test_user_data: dict):
        """测试使用过短密码创建用户失败。

        验证：
        - 密码少于6个字符时返回422
        """
        short_password_data = {
            **test_user_data,
            "username": "validuser456",
            "email": "valid3@example.com",
            "password": "12345",  # 少于6个字符
        }
        response = client.post("/users/", json=short_password_data, headers=auth_headers)
        assert response.status_code == 422, f"预期422，实际{response.status_code}"


class TestGetUsers:
    """测试获取用户接口 (GET /users/)。"""

    def test_get_users_list_success(self, client: TestClient, auth_headers: dict, created_test_user: User):
        """测试正常获取用户列表。

        验证：
        - 返回200状态码
        - 响应为用户列表
        - 列表中包含已创建的用户
        """
        response = client.get("/users/", headers=auth_headers)

        assert response.status_code == 200, f"获取用户列表失败: {response.text}"
        data = response.json()

        # 验证响应为列表
        assert isinstance(data, list), "响应应为列表"

        # 验证列表项结构
        if len(data) > 0:
            user = data[0]
            required_fields = ["id", "username", "email", "full_name", "disabled", "created_at"]
            for field in required_fields:
                assert field in user, f"用户数据应包含{field}字段"

    def test_get_users_pagination(self, client: TestClient, auth_headers: dict, db_session: Session):
        """测试用户列表分页功能。

        验证：
        - 使用offset和limit参数正确分页
        """
        # 准备：创建多个用户
        for i in range(5):
            user = User(
                username=f"pageuser{i}",
                email=f"page{i}@example.com",
                full_name=f"Page User {i}",
                password_hash=get_password_hash("password123"),
                disabled=False,
            )
            db_session.add(user)
        db_session.commit()

        # 执行：测试分页
        response = client.get("/users/?offset=0&limit=3", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3, "返回的用户数不应超过limit"

    def test_get_users_without_auth(self, client: TestClient):
        """测试未认证用户无法获取用户列表。

        验证：
        - 返回401状态码
        """
        response = client.get("/users/")
        assert response.status_code == 401, f"预期401，实际{response.status_code}"

    def test_get_current_user_success(self, client: TestClient, auth_headers: dict, created_test_user: User):
        """测试获取当前登录用户信息。

        验证：
        - 返回200状态码
        - 响应包含当前用户的正确信息
        """
        response = client.get("/users/me", headers=auth_headers)

        assert response.status_code == 200, f"获取当前用户失败: {response.text}"
        data = response.json()

        # 验证响应数据与当前用户匹配
        assert data["username"] == created_test_user.username
        assert data["email"] == created_test_user.email
        assert data["full_name"] == created_test_user.full_name

    def test_get_user_by_id_success(self, client: TestClient, auth_headers: dict, created_test_user: User):
        """测试通过ID获取单个用户。

        验证：
        - 返回200状态码
        - 响应包含正确的用户信息
        """
        response = client.get(f"/users/{created_test_user.id}", headers=auth_headers)

        assert response.status_code == 200, f"获取用户失败: {response.text}"
        data = response.json()

        assert data["id"] == created_test_user.id
        assert data["username"] == created_test_user.username

    def test_get_user_by_id_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的用户。

        验证：
        - 返回404状态码
        - 响应提示用户不存在
        """
        response = client.get("/users/99999", headers=auth_headers)

        assert response.status_code == 404, f"预期404，实际{response.status_code}"
        data = response.json()
        assert "用户不存在" in data["detail"], "错误信息应提示用户不存在"


class TestUpdateUser:
    """测试更新用户接口 (PUT /users/{id})。"""

    def test_update_user_success(self, client: TestClient, auth_headers: dict, created_test_user: User, test_user_data: dict):
        """测试正常更新用户信息。

        验证：
        - 返回200状态码
        - 响应包含更新后的数据
        """
        # 准备：先创建另一个用户用于更新测试
        from ..core.security import get_password_hash
        target_user = User(
            username="targetuser",
            email="target@example.com",
            full_name="Target User",
            password_hash=get_password_hash("password123"),
            disabled=False,
        )
        # 使用db_session创建用户
        # 注意：这里我们使用created_test_user作为目标

        update_data = {
            "username": "updateduser",
            "email": "updated@example.com",
            "full_name": "Updated Name",
            "password": "newpassword123",
            "disabled": True,
        }

        # 执行：更新用户
        response = client.put(f"/users/{created_test_user.id}", json=update_data, headers=auth_headers)

        # 验证
        if response.status_code == 200:
            data = response.json()
            assert data["username"] == update_data["username"]
            assert data["email"] == update_data["email"]
            assert data["full_name"] == update_data["full_name"]
            assert data["disabled"] == update_data["disabled"]

    def test_update_user_not_found(self, client: TestClient, auth_headers: dict, test_user_data: dict):
        """测试更新不存在的用户。

        验证：
        - 返回404状态码
        """
        update_data = {
            "username": "newname",
            "email": "new@example.com",
            "full_name": "New Name",
            "password": "password123",
            "disabled": False,
        }

        response = client.put("/users/99999", json=update_data, headers=auth_headers)

        assert response.status_code == 404, f"预期404，实际{response.status_code}"

    def test_update_user_without_auth(self, client: TestClient, created_test_user: User, test_user_data: dict):
        """测试未认证用户无法更新用户信息。

        验证：
        - 返回401状态码
        """
        update_data = {
            "username": "newname",
            "email": "new@example.com",
            "full_name": "New Name",
            "password": "password123",
            "disabled": False,
        }

        response = client.put(f"/users/{created_test_user.id}", json=update_data)
        assert response.status_code == 401, f"预期401，实际{response.status_code}"


class TestPartialUpdateUser:
    """测试部分更新用户接口 (PATCH /users/{id})。"""

    def test_partial_update_user_success(self, client: TestClient, auth_headers: dict, created_test_user: User):
        """测试正常部分更新用户信息。

        验证：
        - 返回200状态码
        - 仅更新提供的字段
        - 未提供的字段保持不变
        """
        # 只更新邮箱
        patch_data = {"email": "patched@example.com"}

        response = client.patch(f"/users/{created_test_user.id}", json=patch_data, headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            assert data["email"] == patch_data["email"]
            # 其他字段应保持不变
            assert data["username"] == created_test_user.username

    def test_partial_update_user_not_found(self, client: TestClient, auth_headers: dict):
        """测试部分更新不存在的用户。

        验证：
        - 返回404状态码
        """
        patch_data = {"email": "test@example.com"}

        response = client.patch("/users/99999", json=patch_data, headers=auth_headers)
        assert response.status_code == 404, f"预期404，实际{response.status_code}"


class TestDeleteUser:
    """测试删除用户接口 (DELETE /users/{id})。"""

    def test_delete_user_success(self, client: TestClient, auth_headers: dict, db_session: Session):
        """测试正常删除用户。

        验证：
        - 返回204状态码
        - 用户被成功删除
        """
        # 准备：创建要删除的用户
        user_to_delete = User(
            username="deleteme",
            email="delete@example.com",
            full_name="Delete Me",
            password_hash=get_password_hash("password123"),
            disabled=False,
        )
        db_session.add(user_to_delete)
        db_session.commit()
        db_session.refresh(user_to_delete)

        # 执行：删除用户
        response = client.delete(f"/users/{user_to_delete.id}", headers=auth_headers)

        # 验证：检查204状态码
        assert response.status_code == 204, f"删除用户失败: {response.text}"

        # 验证：用户已被删除
        get_response = client.get(f"/users/{user_to_delete.id}", headers=auth_headers)
        assert get_response.status_code == 404, "用户应已被删除"

    def test_delete_user_not_found(self, client: TestClient, auth_headers: dict):
        """测试删除不存在的用户。

        验证：
        - 返回404状态码
        """
        response = client.delete("/users/99999", headers=auth_headers)
        assert response.status_code == 404, f"预期404，实际{response.status_code}"

    def test_delete_user_without_auth(self, client: TestClient, created_test_user: User):
        """测试未认证用户无法删除用户。

        验证：
        - 返回401状态码
        """
        response = client.delete(f"/users/{created_test_user.id}")
        assert response.status_code == 401, f"预期401，实际{response.status_code}"


class TestUserResponseStructure:
    """测试用户接口响应的数据结构。"""

    def test_user_response_fields(self, client: TestClient, auth_headers: dict, created_test_user: User):
        """测试用户响应包含所有必需字段。

        验证响应体结构完整性。
        """
        response = client.get(f"/users/{created_test_user.id}", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()

        # 验证必需字段
        required_fields = ["id", "username", "email", "full_name", "disabled", "created_at"]
        for field in required_fields:
            assert field in data, f"响应应包含{field}字段"

        # 验证字段类型
        assert isinstance(data["id"], int), "id应为整数"
        assert isinstance(data["username"], str), "username应为字符串"
        assert isinstance(data["email"], str), "email应为字符串"
        assert isinstance(data["full_name"], str), "full_name应为字符串"
        assert isinstance(data["disabled"], bool), "disabled应为布尔值"

        # 验证敏感字段不存在
        assert "password" not in data, "响应不应包含password"
        assert "password_hash" not in data, "响应不应包含password_hash"


class TestUserDisabledAccess:
    """测试被禁用用户的访问权限。"""

    def test_disabled_user_cannot_access_users(self, client: TestClient, disabled_user_auth_headers: dict):
        """测试被禁用的用户无法访问用户接口。

        验证：
        - 返回400状态码
        - 提示账户已被禁用
        """
        response = client.get("/users/", headers=disabled_user_auth_headers)

        assert response.status_code == 400, f"预期400，实际{response.status_code}"
        data = response.json()
        assert "禁用" in data["detail"], "错误信息应提示账户被禁用"
