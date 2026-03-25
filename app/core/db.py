"""数据库配置和会话管理模块。

本模块提供数据库连接、会话管理和表创建功能，基于SQLModel和SQLite数据库。

Attributes:
    connect_args: SQLite连接参数配置
    engine: SQLModel数据库引擎实例
    SessionDep: FastAPI依赖注入的会话类型注解
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

connect_args: dict[str, bool] = {"check_same_thread": False}
engine = create_engine(settings.sqlite_url, connect_args=connect_args)


def create_db_and_tables() -> None:
    """创建数据库和所有定义的表。

    根据SQLModel元数据创建所有已定义模型的数据库表。
    如果表已存在，则不会重复创建。

    Note:
        此函数应在应用启动时调用一次。
    """
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """获取数据库会话的依赖生成器。

    创建一个新的数据库会话并在请求完成后自动关闭。
    用于FastAPI的依赖注入系统。

    Yields:
        Session: SQLModel数据库会话实例

    Example:
        在FastAPI路由中使用:
        ```python
        @app.get("/items/")
        def read_items(session: SessionDep):
            items = session.exec(select(Item)).all()
            return items
        ```
    """
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
