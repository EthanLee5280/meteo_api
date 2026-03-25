"""FastAPI应用主模块。

本模块创建并配置FastAPI应用实例，包括数据库初始化和路由注册。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .core.db import create_db_and_tables
from .routers import alerts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理器。

    在应用启动时创建数据库和表，在关闭时执行清理操作。

    Args:
        app: FastAPI应用实例
    """
    # 启动时执行
    create_db_and_tables()
    yield
    # 关闭时执行（如果需要）


app = FastAPI(lifespan=lifespan)
app.include_router(alerts.router)
