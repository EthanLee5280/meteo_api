"""用户相关的 Pydantic 模型。

提供用户创建、更新和响应的数据验证模型。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """用户基础模型。

    包含用户共有的字段。
    """

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., max_length=100, description="电子邮箱")
    full_name: str = Field(..., min_length=1, max_length=100, description="用户全名")
    disabled: bool = Field(default=False, description="账户是否禁用")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """验证用户名格式。"""
        if not v.isalnum():
            raise ValueError("用户名只能包含字母和数字")
        return v.lower()

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """验证全名格式。"""
        return v.strip()


class UserCreate(UserBase):
    """用户创建请求模型。

    用于创建新用户时的数据验证。
    """

    password: str = Field(..., min_length=6, max_length=128, description="明文密码")


class UserUpdate(BaseModel):
    """用户更新请求模型。

    用于部分更新用户信息时的数据验证。所有字段都是可选的。
    """

    username: Optional[str] = Field(default=None, min_length=3, max_length=50, description="用户名")
    email: Optional[EmailStr] = Field(default=None, max_length=100, description="电子邮箱")
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=100, description="用户全名")
    password: Optional[str] = Field(default=None, min_length=6, max_length=128, description="明文密码")
    disabled: Optional[bool] = Field(default=None, description="账户是否禁用")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """验证用户名格式。"""
        if v is None:
            return v
        if not v.isalnum():
            raise ValueError("用户名只能包含字母和数字")
        return v.lower()

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        """验证全名格式。"""
        if v is None:
            return v
        return v.strip()


class UserResponse(BaseModel):
    """用户响应模型。

    用于 API 返回用户信息，不包含敏感字段如密码。
    """

    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="电子邮箱")
    full_name: str = Field(..., description="用户全名")
    disabled: bool = Field(..., description="账户是否禁用")
    created_at: datetime = Field(..., description="账户创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="最后更新时间")

    class Config:
        """Pydantic 配置。"""

        from_attributes = True


class UserInDB(UserResponse):
    """数据库中的用户模型（包含密码哈希）。

    仅用于内部使用，不对外暴露。
    """

    password_hash: str = Field(..., description="密码哈希值")
