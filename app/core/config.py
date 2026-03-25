"""应用配置模块。

本模块提供应用配置管理，支持从环境变量和.env文件加载配置。
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类。

    管理所有应用配置项，支持从环境变量和.env文件加载。

    Attributes:
        sqlite_url: SQLite数据库连接URL
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    sqlite_url: str = Field(
        default="sqlite:///./database.db",
        description="SQLite数据库连接URL",
        pattern=r"^sqlite:///.*$",
    )

    secret_key: str = Field(
        default="35c90dc5b8c019303926cde11205f2af29ff4a96b5071bf32f2a629c1a5706d3",
        description="应用密钥，用于加密敏感数据",
        min_length=64,
        max_length=64,
    )

    algorithm: str = Field(
        default="HS256",
        description="加密算法，默认HS256",
    )

    access_token_expire_minutes: int = Field(
        default=30,
        description="访问令牌过期时间，默认30分钟",
    )


settings = Settings()
