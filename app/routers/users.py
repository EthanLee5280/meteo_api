"""用户路由模块。

提供用户信息的CRUD操作API端点。
"""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select

from ..core.db import SessionDep
from ..core.models import User
from ..core.security import get_password_hash
from ..dependencies import get_current_active_user
from ..schemas.users import UserCreate, UserResponse, UserUpdate

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/users",
    tags=["users"],
)

USER_NOT_FOUND = "用户不存在"
USERNAME_EXISTS = "用户名已存在"
EMAIL_EXISTS = "邮箱已存在"

CurrentUser = Annotated[User, Depends(get_current_active_user)]


def _user_to_response(user: User) -> UserResponse:
    """将数据库用户模型转换为响应模型。

    Args:
        user: 数据库用户模型

    Returns:
        用户响应模型
    """
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> UserResponse:
    """创建新用户。

    Args:
        user_data: 用户创建数据
        session: 数据库会话依赖
        current_user: 当前认证用户

    Returns:
        创建的用户响应对象

    Raises:
        HTTPException: 用户名或邮箱已存在时返回400
    """
    # 检查用户名是否已存在
    existing_user = session.exec(select(User).where(User.username == user_data.username)).first()
    if existing_user:
        logger.warning(f"Username already exists: {user_data.username}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=USERNAME_EXISTS)

    # 检查邮箱是否已存在
    existing_email = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing_email:
        logger.warning(f"Email already exists: {user_data.email}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=EMAIL_EXISTS)

    # 创建用户数据库模型
    user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        disabled=user_data.disabled,
        password_hash=get_password_hash(user_data.password),
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info(f"User {current_user.username} created user: id={user.id}, username={user.username}")
    return _user_to_response(user)


@router.get("/", response_model=list[UserResponse])
def read_users(
    session: SessionDep,
    current_user: CurrentUser,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
) -> list[UserResponse]:
    """获取用户列表。

    Args:
        session: 数据库会话依赖
        current_user: 当前认证用户
        offset: 分页偏移量
        limit: 每页数量，最大100

    Returns:
        用户响应列表
    """
    statement = select(User).offset(offset).limit(limit)
    users = session.exec(statement).all()
    return [_user_to_response(user) for user in users]


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: CurrentUser) -> UserResponse:
    """获取当前登录用户信息。

    Args:
        current_user: 当前认证用户

    Returns:
        当前用户响应对象
    """
    return _user_to_response(current_user)


@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    user_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> UserResponse:
    """获取单个用户。

    Args:
        user_id: 用户ID
        session: 数据库会话依赖
        current_user: 当前认证用户

    Returns:
        用户响应对象

    Raises:
        HTTPException: 用户不存在时返回404
    """
    user = session.get(User, user_id)
    if not user:
        logger.warning(f"User not found: id={user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND)
    return _user_to_response(user)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> UserResponse:
    """完全更新用户信息。

    Args:
        user_id: 用户ID
        user_data: 更新的用户数据
        session: 数据库会话依赖
        current_user: 当前认证用户

    Returns:
        更新后的用户响应对象

    Raises:
        HTTPException: 用户不存在时返回404
    """
    user = session.get(User, user_id)
    if not user:
        logger.warning(f"User not found for update: id={user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND)

    # 检查用户名是否与其他用户冲突
    if user_data.username != user.username:
        existing_user = session.exec(select(User).where(User.username == user_data.username)).first()
        if existing_user and existing_user.id != user_id:
            logger.warning(f"Username already exists: {user_data.username}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=USERNAME_EXISTS)

    # 检查邮箱是否与其他用户冲突
    if user_data.email != user.email:
        existing_email = session.exec(select(User).where(User.email == user_data.email)).first()
        if existing_email and existing_email.id != user_id:
            logger.warning(f"Email already exists: {user_data.email}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=EMAIL_EXISTS)

    # 更新用户字段
    user.username = user_data.username
    user.email = user_data.email
    user.full_name = user_data.full_name
    user.disabled = user_data.disabled
    user.password_hash = get_password_hash(user_data.password)
    user.updated_at = datetime.now(timezone.utc)

    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info(f"User {current_user.username} updated user: id={user.id}, username={user.username}")
    return _user_to_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
def partial_update_user(
    user_id: int,
    user_data: UserUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> UserResponse:
    """部分更新用户信息。

    Args:
        user_id: 用户ID
        user_data: 部分更新的用户数据
        session: 数据库会话依赖
        current_user: 当前认证用户

    Returns:
        更新后的用户响应对象

    Raises:
        HTTPException: 用户不存在时返回404
    """
    user = session.get(User, user_id)
    if not user:
        logger.warning(f"User not found for partial update: id={user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND)

    # 检查用户名是否与其他用户冲突
    if user_data.username is not None and user_data.username != user.username:
        existing_user = session.exec(select(User).where(User.username == user_data.username)).first()
        if existing_user and existing_user.id != user_id:
            logger.warning(f"Username already exists: {user_data.username}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=USERNAME_EXISTS)

    # 检查邮箱是否与其他用户冲突
    if user_data.email is not None and user_data.email != user.email:
        existing_email = session.exec(select(User).where(User.email == user_data.email)).first()
        if existing_email and existing_email.id != user_id:
            logger.warning(f"Email already exists: {user_data.email}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=EMAIL_EXISTS)

    # 应用更新（仅更新提供的字段）
    if user_data.username is not None:
        user.username = user_data.username
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.disabled is not None:
        user.disabled = user_data.disabled
    if user_data.password is not None:
        user.password_hash = get_password_hash(user_data.password)

    user.updated_at = datetime.now(timezone.utc)

    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info(f"User {current_user.username} partially updated user: id={user.id}, username={user.username}")
    return _user_to_response(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    """删除用户。

    Args:
        user_id: 用户ID
        session: 数据库会话依赖
        current_user: 当前认证用户

    Raises:
        HTTPException: 用户不存在时返回404
    """
    user = session.get(User, user_id)
    if not user:
        logger.warning(f"User not found for deletion: id={user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND)
    session.delete(user)
    session.commit()
    logger.info(f"User {current_user.username} deleted user: id={user_id}")
