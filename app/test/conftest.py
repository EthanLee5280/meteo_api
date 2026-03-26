"""测试配置模块。

提供测试所需的fixtures、临时数据库配置和通用测试工具。
"""

import os
import tempfile
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Annotated
from unittest.mock import patch, MagicMock

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.core.db import get_session
from app.core.models import Alert, User
from app.core.security import create_access_token, get_password_hash
from app.dependencies import get_current_active_user
from app.main import app


@pytest.fixture(name="temp_db_file")
def temp_db_file_fixture() -> Generator[str, None, None]:
    """创建临时数据库文件。

    在测试开始前创建临时文件，测试结束后自动删除。
    使用yield确保资源正确清理。

    Yields:
        str: 临时数据库文件路径
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture(name="test_engine")
def test_engine_fixture(temp_db_file: str):
    """创建测试用数据库引擎。

    使用临时数据库文件创建独立的SQLModel引擎，
    确保测试不会影响真实数据库。

    Args:
        temp_db_file: 临时数据库文件路径

    Returns:
        Engine: SQLModel数据库引擎
    """
    sqlite_url = f"sqlite:///{temp_db_file}"
    connect_args = {"check_same_thread": False}
    engine = create_engine(sqlite_url, connect_args=connect_args, echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(test_engine) -> Generator[Session, None, None]:
    """创建测试用数据库会话。

    为每个测试提供独立的数据库会话，测试结束后自动关闭。
    这是替代FastAPI依赖注入的核心fixture。

    Args:
        test_engine: 测试用数据库引擎

    Yields:
        Session: SQLModel数据库会话
    """
    with Session(test_engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    """创建测试客户端。

    通过覆盖依赖注入，使用测试数据库会话替代真实数据库。
    这是FastAPI测试的核心模式，确保测试隔离性。

    Args:
        session: 测试用数据库会话

    Yields:
        TestClient: FastAPI测试客户端
    """

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session) -> User:
    """创建测试用户。

    在测试数据库中创建一个标准测试用户，用于认证测试。
    用户信息包含完整的必填字段。

    Args:
        session: 测试用数据库会话

    Returns:
        User: 创建的测试用户对象
    """
    user = User(
        username="testuser",
        email="testuser@example.com",
        full_name="Test User",
        password_hash=get_password_hash("testpassword123"),
        disabled=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="disabled_user")
def disabled_user_fixture(session: Session) -> User:
    """创建被禁用的测试用户。

    用于测试禁用用户无法登录的场景。

    Args:
        session: 测试用数据库会话

    Returns:
        User: 被禁用的测试用户对象
    """
    user = User(
        username="disableduser",
        email="disabled@example.com",
        full_name="Disabled User",
        password_hash=get_password_hash("testpassword123"),
        disabled=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(test_user: User) -> dict[str, str]:
    """创建认证请求头。

    为测试用户生成JWT令牌，并封装为Authorization请求头。
    用于需要认证的API测试。

    Args:
        test_user: 测试用户对象

    Returns:
        dict: 包含Authorization头的字典
    """
    access_token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(name="test_alert")
def test_alert_fixture(session: Session, test_user: User) -> Alert:
    """创建测试预警信息。

    在测试数据库中创建一个标准预警记录，用于预警相关测试。

    Args:
        session: 测试用数据库会话
        test_user: 测试用户（用于publisher字段）

    Returns:
        Alert: 创建的测试预警对象
    """
    from datetime import datetime, timezone

    alert = Alert(
        alert_type="暴雨",
        alert_level="红色",
        alert_name="暴雨红色预警",
        alert_description="预计未来3小时内将出现特大暴雨",
        alert_time=datetime.now(timezone.utc),
        location="北京市朝阳区",
        longitude=116.48,
        latitude=39.92,
        publisher=test_user.username,
    )
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert


@pytest.fixture(name="mock_current_user")
def mock_current_user_fixture(test_user: User):
    """模拟当前用户依赖。

    通过patch方式模拟get_current_active_user依赖，
    用于需要绕过认证的测试场景。

    Args:
        test_user: 要模拟的当前用户

    Yields:
        patch: mock上下文管理器
    """
    with patch("app.dependencies.get_current_active_user", return_value=test_user):
        yield test_user


def assert_response_structure(response_data: dict, expected_fields: list[str]) -> None:
    """验证响应数据结构。

    检查响应数据是否包含所有期望的字段。

    Args:
        response_data: 响应数据字典
        expected_fields: 期望的字段列表

    Raises:
        AssertionError: 缺少字段时抛出
    """
    for field in expected_fields:
        assert field in response_data, f"响应缺少必需字段: {field}"


def assert_user_response_structure(response_data: dict) -> None:
    """验证用户响应数据结构。

    检查用户响应是否包含所有必需字段。

    Args:
        response_data: 用户响应数据字典
    """
    expected_fields = ["id", "username", "email", "full_name", "disabled", "created_at"]
    assert_response_structure(response_data, expected_fields)
    assert "password" not in response_data, "响应不应包含密码字段"
    assert "password_hash" not in response_data, "响应不应包含密码哈希字段"


def assert_alert_response_structure(response_data: dict) -> None:
    """验证预警响应数据结构。

    检查预警响应是否包含所有必需字段。

    Args:
        response_data: 预警响应数据字典
    """
    expected_fields = [
        "id",
        "alert_type",
        "alert_level",
        "alert_name",
        "alert_description",
        "alert_time",
        "location",
        "longitude",
        "latitude",
        "publisher",
        "create_at",
    ]
    assert_response_structure(response_data, expected_fields)
