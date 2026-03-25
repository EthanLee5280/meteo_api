from datetime import datetime, timezone

from pydantic import field_validator
from sqlmodel import SQLModel, Field


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
