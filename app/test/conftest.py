"""测试配置文件。

提供测试所需的fixtures，包括临时数据库、测试客户端、认证令牌等。
所有测试共享这些fixtures以确保测试环境的一致性。
"""

import os
import tempfile
from datetime import datetime, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from ..core.db import get_session
from ..core.models import Alert, User
from ..core.security import create_access_token, get_password_hash
from ..main import app


# =============================================================================
# 数据库 Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def test_db_path() -> str:
    """创建临时数据库文件路径。

    在整个测试会话期间使用同一个临时数据库文件，
    测试结束后自动清理。

    Returns:
        临时数据库文件的绝对路径
    """
    # 创建临时文件，关闭后不会立即删除
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # 测试会话结束后清理临时数据库文件
    os.unlink(path)


@pytest.fixture(scope="function")
def db_engine(test_db_path: str):
    """创建测试数据库引擎。

    每个测试函数使用独立的引擎实例，确保测试隔离性。
    使用StaticPool确保在同一线程中共享连接。

    Args:
        test_db_path: 临时数据库文件路径

    Yields:
        SQLModel数据库引擎实例
    """
    # 创建内存数据库引擎，使用StaticPool确保同一线程共享连接
    engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # 创建所有表结构
    SQLModel.metadata.create_all(engine)
    yield engine
    # 清理：删除所有表
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """创建数据库会话。

    为每个测试函数提供独立的数据库会话，
    测试结束后自动回滚所有更改，确保测试隔离性。

    Args:
        db_engine: 数据库引擎fixture

    Yields:
        SQLModel数据库会话实例
    """
    with Session(db_engine) as session:
        yield session
        # 测试结束后回滚所有未提交的事务
        session.rollback()


# =============================================================================
# 测试客户端 Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """创建FastAPI测试客户端。

    使用临时数据库会话替代真实数据库依赖，
    确保测试不依赖外部数据库。

    Args:
        db_session: 数据库会话fixture

    Yields:
        FastAPI TestClient实例
    """
    # 定义依赖替换函数，使用测试会话替代真实会话
    def override_get_session() -> Generator[Session, None, None]:
        yield db_session

    # 替换应用的依赖项
    app.dependency_overrides[get_session] = override_get_session

    # 创建测试客户端
    with TestClient(app) as test_client:
        yield test_client

    # 测试结束后清理依赖替换
    app.dependency_overrides.clear()


# =============================================================================
# 测试数据 Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def test_user_data() -> dict:
    """提供标准测试用户数据。

    Returns:
        包含测试用户信息的字典
    """
    return {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "testpass123",
        "disabled": False,
    }


@pytest.fixture(scope="function")
def test_user_disabled_data() -> dict:
    """提供被禁用的测试用户数据。

    Returns:
        包含被禁用测试用户信息的字典
    """
    return {
        "username": "disableduser",
        "email": "disabled@example.com",
        "full_name": "Disabled User",
        "password": "disabledpass123",
        "disabled": True,
    }


@pytest.fixture(scope="function")
def test_alert_data() -> dict:
    """提供标准测试预警数据（用于API请求，alert_time为ISO字符串格式）。

    Returns:
        包含测试预警信息的字典
    """
    return {
        "alert_type": "台风",
        "alert_level": "红色",
        "alert_name": "台风红色预警",
        "alert_description": "预计未来24小时内将有强台风登陆",
        "alert_time": datetime.now(timezone.utc).isoformat(),  # API请求使用ISO字符串
        "location": "广东省深圳市",
        "longitude": 114.0579,
        "latitude": 22.5431,
        "publisher": "气象台",
    }


@pytest.fixture(scope="function")
def test_alert_data_for_db() -> dict:
    """提供标准测试预警数据（用于数据库直接操作，alert_time为datetime对象）。

    Returns:
        包含测试预警信息的字典
    """
    return {
        "alert_type": "台风",
        "alert_level": "红色",
        "alert_name": "台风红色预警",
        "alert_description": "预计未来24小时内将有强台风登陆",
        "alert_time": datetime.now(timezone.utc),  # 数据库操作使用datetime对象
        "location": "广东省深圳市",
        "longitude": 114.0579,
        "latitude": 22.5431,
        "publisher": "气象台",
    }


# =============================================================================
# 数据库实体 Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def created_test_user(db_session: Session, test_user_data: dict) -> User:
    """在数据库中创建测试用户。

    Args:
        db_session: 数据库会话
        test_user_data: 测试用户数据

    Returns:
        已创建的User数据库模型实例
    """
    user = User(
        username=test_user_data["username"],
        email=test_user_data["email"],
        full_name=test_user_data["full_name"],
        password_hash=get_password_hash(test_user_data["password"]),
        disabled=test_user_data["disabled"],
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def created_disabled_user(db_session: Session, test_user_disabled_data: dict) -> User:
    """在数据库中创建被禁用的测试用户。

    Args:
        db_session: 数据库会话
        test_user_disabled_data: 被禁用的测试用户数据

    Returns:
        已创建的禁用User数据库模型实例
    """
    user = User(
        username=test_user_disabled_data["username"],
        email=test_user_disabled_data["email"],
        full_name=test_user_disabled_data["full_name"],
        password_hash=get_password_hash(test_user_disabled_data["password"]),
        disabled=test_user_disabled_data["disabled"],
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def created_test_alert(db_session: Session, created_test_user: User, test_alert_data_for_db: dict) -> Alert:
    """在数据库中创建测试预警。

    Args:
        db_session: 数据库会话
        created_test_user: 已创建的测试用户（作为创建者上下文）
        test_alert_data_for_db: 测试预警数据（数据库格式）

    Returns:
        已创建的Alert数据库模型实例
    """
    alert = Alert(**test_alert_data_for_db)
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return alert


# =============================================================================
# 认证 Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def auth_token(created_test_user: User) -> str:
    """生成测试用户的认证令牌。

    Args:
        created_test_user: 已创建的测试用户

    Returns:
        JWT访问令牌字符串
    """
    return create_access_token(data={"sub": created_test_user.username})


@pytest.fixture(scope="function")
def auth_headers(auth_token: str) -> dict:
    """提供认证请求头。

    Args:
        auth_token: 认证令牌

    Returns:
        包含Authorization头的字典
    """
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="function")
def disabled_user_token(created_disabled_user: User) -> str:
    """生成被禁用用户的认证令牌。

    Args:
        created_disabled_user: 已创建的被禁用用户

    Returns:
        JWT访问令牌字符串
    """
    return create_access_token(data={"sub": created_disabled_user.username})


@pytest.fixture(scope="function")
def disabled_user_auth_headers(disabled_user_token: str) -> dict:
    """提供被禁用用户的认证请求头。

    Args:
        disabled_user_token: 被禁用用户的认证令牌

    Returns:
        包含Authorization头的字典
    """
    return {"Authorization": f"Bearer {disabled_user_token}"}
