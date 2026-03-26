"""
Pytest配置文件，包含测试fixture和数据库设置。

本文件提供：
1. 临时SQLite数据库配置
2. 测试客户端fixture
3. 认证用户fixture
4. 依赖项覆盖fixture
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from ..core.models import User
from ..core.security import create_access_token, get_password_hash
from ..core.db import get_session
from ..dependencies import get_current_user
from ..main import app


# 测试数据库配置
# 使用内存中的SQLite数据库，避免影响真实数据
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(name="test_engine")
def test_engine_fixture():
    """
    创建测试数据库引擎fixture。
    
    使用内存数据库和StaticPool确保线程安全。
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # 创建所有表
    SQLModel.metadata.create_all(engine)
    yield engine
    # 测试完成后清理
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="test_session")
def test_session_fixture(test_engine):
    """
    创建测试数据库会话fixture。
    
    每个测试用例都获得一个新的会话，确保测试隔离。
    """
    with Session(test_engine) as session:
        yield session


@pytest.fixture(name="test_user")
def test_user_fixture(test_session: Session):
    """
    创建测试用户fixture。
    
    返回一个已保存到数据库的普通用户实例。
    """
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password_hash=get_password_hash("testpass123"),
        disabled=False,
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


@pytest.fixture(name="test_admin_user")
def test_admin_user_fixture(test_session: Session):
    """
    创建管理员测试用户fixture。
    
    返回一个已保存到数据库的管理员用户实例。
    """
    user = User(
        username="adminuser",
        email="admin@example.com",
        full_name="Admin User",
        password_hash=get_password_hash("adminpass123"),
        disabled=False,
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


@pytest.fixture(name="user_token_headers")
def user_token_headers_fixture(test_user: User):
    """
    创建普通用户的认证token请求头fixture。
    
    返回包含Bearer token的请求头字典。
    """
    access_token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(name="admin_token_headers")
def admin_token_headers_fixture(test_admin_user: User):
    """
    创建管理员用户的认证token请求头fixture。
    
    返回包含Bearer token的请求头字典。
    """
    access_token = create_access_token(data={"sub": test_admin_user.username})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(name="client")
def client_fixture(test_session: Session, test_user: User):
    """
    创建FastAPI测试客户端fixture。
    
    覆盖依赖项：
    - get_session: 使用测试数据库会话
    - get_current_user: 返回测试用户
    
    这样测试时不会使用真实数据库，也不需要真实认证。
    """
    # 覆盖数据库会话依赖
    def override_get_session():
        yield test_session

    # 覆盖当前用户依赖
    def override_get_current_user():
        return test_user

    # 应用依赖覆盖
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user

    # 创建测试客户端
    with TestClient(app) as client:
        yield client

    # 测试完成后清理依赖覆盖
    app.dependency_overrides.clear()


@pytest.fixture(name="unauthenticated_client")
def unauthenticated_client_fixture(test_session: Session):
    """
    创建未认证的测试客户端fixture。
    
    仅覆盖数据库会话依赖，用于测试认证相关接口。
    """
    def override_get_session():
        yield test_session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
