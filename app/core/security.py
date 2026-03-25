"""安全相关工具模块。

提供密码哈希、JWT令牌生成和验证等安全功能。
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from fastapi import HTTPException, status
from pwdlib import PasswordHash

from .config import settings

password_hasher = PasswordHash.recommended()

ALGORITHM = settings.algorithm
SECRET_KEY = settings.secret_key
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="无法验证凭据",
    headers={"WWW-Authenticate": "Bearer"},
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希密码是否匹配。

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        密码是否匹配
    """
    return password_hasher.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """对密码进行哈希加密。

    Args:
        password: 明文密码

    Returns:
        哈希后的密码
    """
    return password_hasher.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """创建JWT访问令牌。

    Args:
        data: 要编码到令牌中的数据，通常包含用户标识
        expires_delta: 令牌过期时间，默认为配置中的access_token_expire_minutes

    Returns:
        编码后的JWT令牌字符串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """解码并验证JWT访问令牌。

    Args:
        token: JWT令牌字符串

    Returns:
        解码后的令牌数据

    Raises:
        HTTPException: 令牌无效或过期时抛出401错误
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise CREDENTIALS_EXCEPTION
