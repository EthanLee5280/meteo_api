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


settings = Settings()
