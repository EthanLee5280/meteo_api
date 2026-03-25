"""初始化管理员用户脚本。

用于创建第一个测试用户，以便进行OAuth2认证测试。
"""

from sqlmodel import Session, SQLModel, select

from app.core.db import engine
from app.core.models import Alert, User
from app.core.security import get_password_hash


def create_admin_user() -> None:
    """创建管理员用户。

    如果用户不存在，则创建一个默认的管理员测试用户。
    """
    # 先创建数据库表
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # 检查是否已存在用户
        existing_user = session.exec(select(User).where(User.username == "admin")).first()
        if existing_user:
            print("管理员用户已存在")
            return

        # 创建管理员用户
        admin_user = User(
            username="admin",
            email="admin@example.com",
            full_name="系统管理员",
            disabled=False,
            password_hash=get_password_hash("admin123"),
        )

        session.add(admin_user)
        session.commit()
        print("管理员用户创建成功")
        print("用户名: admin")
        print("密码: admin123")


if __name__ == "__main__":
    create_admin_user()
