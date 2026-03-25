from datetime import datetime, timezone
from typing import Optional

from pydantic import field_validator, EmailStr
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    """用户数据模型。

    存储用户账户信息，包括登录凭据和个人资料。

    Attributes:
        id: 主键ID
        username: 用户名，唯一标识
        password_hash: 密码哈希值（非明文）
        email: 电子邮箱地址
        full_name: 用户全名
        disabled: 账户是否禁用
        created_at: 账户创建时间
        updated_at: 最后更新时间
    """

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, index=True, unique=True)
    password_hash: str = Field(max_length=255)
    email: EmailStr = Field(max_length=100, index=True)
    full_name: str = Field(max_length=100)
    disabled: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """验证用户名格式。"""
        if len(v) < 3:
            raise ValueError("用户名至少需要3个字符")
        if not v.isalnum():
            raise ValueError("用户名只能包含字母和数字")
        return v.lower()

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """验证全名格式。"""
        if not v.strip():
            raise ValueError("全名不能为空")
        return v.strip()

    def __repr__(self) -> str:
        """返回对象的字符串表示。"""
        return (
            f"User(id={self.id}, username={self.username!r}, "
            f"email={self.email!r}, disabled={self.disabled})"
        )


class Alert(SQLModel, table=True):
    """预警信息数据模型。

    存储气象预警信息，包括预警类型、等级、位置等详细信息。

    Attributes:
        id: 主键ID
        alert_type: 预警类型
        alert_level: 预警等级
        alert_name: 预警名称
        alert_description: 预警描述
        alert_time: 预警发布时间
        location: 预警位置
        longitude: 经度 (-180 到 180)
        latitude: 纬度 (-90 到 90)
        publisher: 发布者
        create_at: 记录创建时间
        update_at: 记录更新时间
    """

    __tablename__ = "alerts"

    id: int | None = Field(default=None, primary_key=True)
    alert_type: str = Field(max_length=50)
    alert_level: str = Field(max_length=20)
    alert_name: str = Field(max_length=100, index=True)
    alert_description: str = Field(max_length=500)
    alert_time: datetime
    location: str = Field(max_length=200)
    longitude: float
    latitude: float
    publisher: str = Field(max_length=100)
    create_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    update_at: datetime | None = Field(default=None)

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        """验证经度范围。"""
        if not -180 <= v <= 180:
            raise ValueError("经度必须在 -180 到 180 之间")
        return v

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        """验证纬度范围。"""
        if not -90 <= v <= 90:
            raise ValueError("纬度必须在 -90 到 90 之间")
        return v

    def __repr__(self) -> str:
        """返回对象的字符串表示。"""
        return (
            f"Alert(id={self.id}, alert_name={self.alert_name!r}, "
            f"alert_type={self.alert_type!r}, alert_level={self.alert_level!r})"
        )
