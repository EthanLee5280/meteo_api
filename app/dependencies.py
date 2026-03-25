"""FastAPI 依赖模块。

提供认证、授权等依赖注入功能。
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import select

from .core.db import SessionDep
from .core.models import User
from .core.security import decode_access_token
from .schemas.auth import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

TokenDep = Annotated[str, Depends(oauth2_scheme)]


async def get_current_user(
    token: TokenDep,
    session: SessionDep,
) -> User:
    """获取当前认证用户。

    从请求中的JWT令牌解析用户身份，并查询数据库获取用户信息。

    Args:
        token: OAuth2 Bearer令牌
        session: 数据库会话

    Returns:
        当前认证用户的数据库模型

    Raises:
        HTTPException: 认证失败时返回401错误
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    username: str | None = payload.get("sub")
    if username is None:
        raise credentials_exception

    token_data = TokenData(username=username)
    if token_data.username is None:
        raise credentials_exception

    user = session.exec(select(User).where(User.username == token_data.username)).first()
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """获取当前活跃用户。

    检查用户账户是否被禁用。

    Args:
        current_user: 当前认证用户

    Returns:
        当前活跃用户

    Raises:
        HTTPException: 用户被禁用时返回400错误
    """
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用",
        )
    return current_user


CurrentUserDep = Annotated[User, Depends(get_current_active_user)]
