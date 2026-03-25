"""生成100条Alert测试数据并插入到数据库.

本脚本生成100条随机的气象预警数据，并插入到SQLite数据库中。
"""

import random
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, create_engine

from app.core.models import Alert


def generate_alert_data(count: int = 100) -> list[Alert]:
    """生成指定数量的Alert测试数据.

    Args:
        count: 需要生成的数据条数，默认为100.

    Returns:
        Alert对象列表.
    """
    alert_types = [
        "台风", "暴雨", "暴雪", "寒潮", "大风", "沙尘暴",
        "高温", "干旱", "雷电", "冰雹", "霜冻", "大雾",
        "霾", "道路结冰", "森林火险", "雷雨大风"
    ]

    alert_levels = ["蓝色", "黄色", "橙色", "红色"]

    locations = [
        "北京市", "上海市", "广州市", "深圳市", "杭州市", "南京市",
        "成都市", "武汉市", "西安市", "重庆市", "天津市", "苏州市",
        "郑州市", "长沙市", "沈阳市", "青岛市", "宁波市", "东莞市",
        "无锡市", "佛山市", "合肥市", "大连市", "福州市", "厦门市",
        "哈尔滨市", "济南市", "温州市", "南宁市", "长春市", "泉州市"
    ]

    publishers = [
        "国家气象中心", "中国气象局", "省级气象台", "市级气象局",
        "中央气象台", "地方气象站"
    ]

    alerts = []
    base_time = datetime.now(timezone.utc)

    for i in range(count):
        alert_type = random.choice(alert_types)
        alert_level = random.choice(alert_levels)
        location = random.choice(locations)
        publisher = random.choice(publishers)

        # 随机生成经纬度（中国范围大致：经度73-135，纬度18-54）
        longitude = round(random.uniform(73.0, 135.0), 6)
        latitude = round(random.uniform(18.0, 54.0), 6)

        # 随机生成预警时间（过去30天内）
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        alert_time = base_time - timedelta(days=days_ago, hours=hours_ago)

        # 生成预警名称和描述
        alert_name = f"{location}{alert_type}{alert_level}预警"
        alert_description = (
            f"预计{location}将出现{alert_type}天气，"
            f"预警等级为{alert_level}，请注意防范。"
        )

        alert = Alert(
            alert_type=alert_type,
            alert_level=alert_level,
            alert_name=alert_name,
            alert_description=alert_description,
            alert_time=alert_time,
            location=location,
            longitude=longitude,
            latitude=latitude,
            publisher=publisher,
        )
        alerts.append(alert)

    return alerts


def insert_alerts_to_db(alerts: list[Alert], db_url: str) -> None:
    """将Alert数据插入到数据库.

    Args:
        alerts: 要插入的Alert对象列表.
        db_url: 数据库连接URL.
    """
    connect_args = {"check_same_thread": False}
    engine = create_engine(db_url, connect_args=connect_args)

    with Session(engine) as session:
        for alert in alerts:
            session.add(alert)
        session.commit()

    print(f"成功插入 {len(alerts)} 条预警数据到数据库")


def main() -> None:
    """主函数：生成数据并插入数据库."""
    db_url = "sqlite:///app/database.db"

    print("开始生成100条Alert测试数据...")
    alerts = generate_alert_data(100)

    print(f"正在将数据插入到数据库: {db_url}")
    insert_alerts_to_db(alerts, db_url)

    print("数据生成完成！")


if __name__ == "__main__":
    main()
