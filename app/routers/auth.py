"""认证路由模块。

提供用户登录、登出等认证相关的API端点。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select

from ..core.db import SessionDep
from ..core.models import User
from ..core.security import create_access_token, verify_password
from ..schemas.auth import Token

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
) -> Token:
    """用户登录获取访问令牌。

    使用OAuth2密码流程进行身份验证，成功返回JWT访问令牌。

    Args:
        form_data: OAuth2密码请求表单，包含username和password
        session: 数据库会话依赖

    Returns:
        包含访问令牌的响应对象

    Raises:
        HTTPException: 认证失败时返回401错误
    """
    # 查询用户
    user = session.exec(select(User).where(User.username == form_data.username)).first()

    # 验证用户存在且密码正确
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查用户是否被禁用
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用",
        )

    # 创建访问令牌
    access_token = create_access_token(data={"sub": user.username})

    return Token(access_token=access_token, token_type="bearer")


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
) -> Token:
    """获取访问令牌（与/login相同，兼容OAuth2标准端点命名）。

    Args:
        form_data: OAuth2密码请求表单
        session: 数据库会话依赖

    Returns:
        包含访问令牌的响应对象
    """
    return await login(form_data, session)
