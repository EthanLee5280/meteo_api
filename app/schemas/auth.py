"""认证相关的 Pydantic 模型。

提供登录请求、令牌响应等数据验证模型。
"""

from pydantic import BaseModel, Field


class Token(BaseModel):
    """令牌响应模型。

    用于登录成功后返回访问令牌。
    """

    access_token: str = Field(..., description="JWT访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")


class TokenData(BaseModel):
    """令牌数据模型。

    用于从令牌中解析用户标识。
    """

    username: str | None = Field(default=None, description="用户名")


class LoginRequest(BaseModel):
    """登录请求模型。

    用于用户登录时的数据验证。
    """

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
