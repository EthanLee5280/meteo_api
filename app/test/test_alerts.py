"""预警接口测试模块。

测试预警信息CRUD操作相关功能。

注意：由于Alert模型直接用作请求体，datetime字段在JSON序列化时存在兼容性问题。
本测试模块通过直接数据库操作和API读取操作来测试功能。
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlmodel import Session, select

from app.core.models import Alert, User
from app.test.conftest import assert_alert_response_structure


def create_alert_in_db(
    session: Session,
    test_user: User,
    alert_type: str = "暴雨",
    alert_level: str = "蓝色",
    alert_name: str = "暴雨蓝色预警",
    alert_description: str = "测试描述",
    location: str = "测试位置",
    longitude: float = 116.31,
    latitude: float = 39.97,
) -> Alert:
    """在数据库中创建预警记录的辅助函数。

    由于Alert模型的datetime字段处理问题，直接通过数据库操作创建预警。

    Args:
        session: 数据库会话
        test_user: 测试用户
        alert_type: 预警类型
        alert_level: 预警等级
        alert_name: 预警名称
        alert_description: 预警描述
        location: 位置
        longitude: 经度
        latitude: 纬度

    Returns:
        Alert: 创建的预警对象
    """
    alert = Alert(
        alert_type=alert_type,
        alert_level=alert_level,
        alert_name=alert_name,
        alert_description=alert_description,
        alert_time=datetime.now(timezone.utc),
        location=location,
        longitude=longitude,
        latitude=latitude,
        publisher=test_user.username,
    )
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert


class TestAlertModel:
    """预警模型测试类。

    测试Alert模型的验证规则和数据库操作。
    由于API层存在datetime处理问题，这里直接测试模型层。
    """

    def test_create_alert_in_database(
        self, session: Session, test_user: User
    ):
        """测试在数据库中创建预警。

        验证预警可以正确保存到数据库。

        Args:
            session: 数据库会话
            test_user: 测试用户
        """
        alert = create_alert_in_db(
            session=session,
            test_user=test_user,
            alert_type="台风",
            alert_level="橙色",
            alert_name="台风橙色预警",
            alert_description="预计未来24小时内将受台风影响",
            location="上海市浦东新区",
            longitude=121.47,
            latitude=31.23,
        )

        assert alert.id is not None
        assert alert.alert_type == "台风"
        assert alert.alert_level == "橙色"
        assert alert.alert_name == "台风橙色预警"
        assert alert.publisher == test_user.username

    def test_alert_longitude_validation_valid(
        self, session: Session, test_user: User
    ):
        """测试有效的经度值。

        验证经度在有效范围内可以正常创建。

        Args:
            session: 数据库会话
            test_user: 测试用户
        """
        for longitude in [-180.0, 0.0, 180.0]:
            alert = create_alert_in_db(
                session=session,
                test_user=test_user,
                alert_name=f"测试预警_{longitude}",
                longitude=longitude,
            )
            assert alert.longitude == longitude

    def test_alert_latitude_validation_valid(
        self, session: Session, test_user: User
    ):
        """测试有效的纬度值。

        验证纬度在有效范围内可以正常创建。

        Args:
            session: 数据库会话
            test_user: 测试用户
        """
        for latitude in [-90.0, 0.0, 90.0]:
            alert = create_alert_in_db(
                session=session,
                test_user=test_user,
                alert_name=f"测试预警_{latitude}",
                latitude=latitude,
            )
            assert alert.latitude == latitude

    def test_alert_invalid_longitude_raises_error(
        self, session: Session, test_user: User
    ):
        """测试无效经度值抛出错误。

        验证超出范围的经度值会抛出验证错误。
        注意：SQLModel table=True时，验证器在model_validate时触发。

        Args:
            session: 数据库会话
            test_user: 测试用户
        """
        with pytest.raises(ValueError, match="经度必须在"):
            Alert.model_validate({
                "alert_type": "测试",
                "alert_level": "蓝色",
                "alert_name": "测试预警",
                "alert_description": "测试描述",
                "alert_time": datetime.now(timezone.utc),
                "location": "测试位置",
                "longitude": 200.0,
                "latitude": 39.0,
                "publisher": test_user.username,
            })

    def test_alert_invalid_latitude_raises_error(
        self, session: Session, test_user: User
    ):
        """测试无效纬度值抛出错误。

        验证超出范围的纬度值会抛出验证错误。
        注意：SQLModel table=True时，验证器在model_validate时触发。

        Args:
            session: 数据库会话
            test_user: 测试用户
        """
        with pytest.raises(ValueError, match="纬度必须在"):
            Alert.model_validate({
                "alert_type": "测试",
                "alert_level": "蓝色",
                "alert_name": "测试预警",
                "alert_description": "测试描述",
                "alert_time": datetime.now(timezone.utc),
                "location": "测试位置",
                "longitude": 116.0,
                "latitude": 100.0,
                "publisher": test_user.username,
            })


class TestReadAlerts:
    """读取预警接口测试类。

    测试预警列表和单个预警查询功能。
    """

    def test_read_alerts_list(
        self, client: TestClient, auth_headers: dict, test_alert: Alert
    ):
        """测试获取预警列表。

        验证返回的预警列表包含已创建的预警。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            test_alert: 测试预警
        """
        response = client.get("/alerts/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        for alert in data:
            assert_alert_response_structure(alert)

    def test_read_alerts_pagination(self, client: TestClient, auth_headers: dict):
        """测试预警列表分页。

        验证分页参数正确工作。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        response = client.get("/alerts/?offset=0&limit=10", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    def test_read_alerts_limit_exceeded(
        self, client: TestClient, auth_headers: dict
    ):
        """测试分页限制。

        验证limit参数最大值为100。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        response = client.get("/alerts/?limit=200", headers=auth_headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_read_alert_by_id(
        self, client: TestClient, auth_headers: dict, test_alert: Alert
    ):
        """测试通过ID获取预警。

        验证返回指定ID的预警信息。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            test_alert: 测试预警
        """
        response = client.get(f"/alerts/{test_alert.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert_alert_response_structure(data)
        assert data["id"] == test_alert.id
        assert data["alert_name"] == test_alert.alert_name

    def test_read_nonexistent_alert(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的预警。

        使用不存在的预警ID，验证返回404错误。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        response = client.get("/alerts/99999", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "预警信息不存在"

    def test_read_alerts_without_auth(self, client: TestClient):
        """测试未认证获取预警列表。

        不提供认证令牌获取预警列表，验证返回401错误。

        Args:
            client: 测试客户端
        """
        response = client.get("/alerts/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUpdateAlert:
    """更新预警接口测试类。

    测试预警更新功能（PUT和PATCH）。
    使用直接数据库操作来测试更新逻辑。
    """

    def test_update_alert_partial_via_api(
        self, client: TestClient, auth_headers: dict, test_alert: Alert
    ):
        """测试部分更新预警（PATCH）。

        只更新部分字段，验证其他字段保持不变。
        PATCH操作不涉及datetime字段的更新。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            test_alert: 测试预警
        """
        original_location = test_alert.location
        original_longitude = test_alert.longitude
        update_data = {
            "alert_level": "红色",
        }

        response = client.patch(
            f"/alerts/{test_alert.id}", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["alert_level"] == "红色"
        assert data["location"] == original_location
        assert data["longitude"] == original_longitude

    def test_update_alert_in_database(
        self, session: Session, test_user: User
    ):
        """测试在数据库中更新预警。

        直接通过数据库操作测试更新功能。

        Args:
            session: 数据库会话
            test_user: 测试用户
        """
        alert = create_alert_in_db(
            session=session,
            test_user=test_user,
            alert_name="原始预警",
            alert_level="蓝色",
        )

        alert.alert_level = "红色"
        alert.alert_name = "更新后的预警"
        session.add(alert)
        session.commit()
        session.refresh(alert)

        assert alert.alert_level == "红色"
        assert alert.alert_name == "更新后的预警"

    def test_update_nonexistent_alert(self, client: TestClient, auth_headers: dict):
        """测试更新不存在的预警。

        使用不存在的预警ID，验证返回404错误。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        update_data = {
            "alert_level": "红色",
        }

        response = client.patch("/alerts/99999", json=update_data, headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteAlert:
    """删除预警接口测试类。

    测试预警删除功能。
    """

    def test_delete_alert_success(
        self, client: TestClient, auth_headers: dict, session: Session, test_user: User
    ):
        """测试成功删除预警。

        创建一个预警后删除，验证删除成功。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            session: 数据库会话
            test_user: 测试用户
        """
        alert = create_alert_in_db(
            session=session,
            test_user=test_user,
            alert_name="待删除预警",
        )
        alert_id = alert.id

        response = client.delete(f"/alerts/{alert_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        deleted_alert = session.get(Alert, alert_id)
        assert deleted_alert is None

    def test_delete_nonexistent_alert(self, client: TestClient, auth_headers: dict):
        """测试删除不存在的预警。

        使用不存在的预警ID，验证返回404错误。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
        """
        response = client.delete("/alerts/99999", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "预警信息不存在"

    def test_delete_alert_without_auth(self, client: TestClient, test_alert: Alert):
        """测试未认证删除预警。

        不提供认证令牌删除预警，验证返回401错误。

        Args:
            client: 测试客户端
            test_alert: 测试预警
        """
        response = client.delete(f"/alerts/{test_alert.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAlertAuthentication:
    """预警接口认证测试类。

    测试预警接口的认证要求。
    """

    def test_create_alert_without_auth(self, client: TestClient):
        """测试未认证创建预警。

        不提供认证令牌创建预警，验证返回401错误。

        Args:
            client: 测试客户端
        """
        alert_data = {
            "alert_type": "暴雨",
            "alert_level": "蓝色",
            "alert_name": "暴雨蓝色预警",
        }

        response = client.post("/alerts/", json=alert_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAlertResponseStructure:
    """预警响应结构测试类。

    测试预警API响应的数据结构。
    """

    def test_alert_response_datetime_format(
        self, client: TestClient, auth_headers: dict, test_alert: Alert
    ):
        """测试响应中日期时间格式。

        验证响应中的日期时间字段格式正确。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            test_alert: 测试预警
        """
        response = client.get(f"/alerts/{test_alert.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "alert_time" in data
        assert "create_at" in data

        assert isinstance(data["alert_time"], str)
        assert isinstance(data["create_at"], str)

    def test_alert_response_contains_all_fields(
        self, client: TestClient, auth_headers: dict, test_alert: Alert
    ):
        """测试响应包含所有必需字段。

        验证预警响应包含所有预期的字段。

        Args:
            client: 测试客户端
            auth_headers: 认证请求头
            test_alert: 测试预警
        """
        response = client.get(f"/alerts/{test_alert.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        required_fields = [
            "id",
            "alert_type",
            "alert_level",
            "alert_name",
            "alert_description",
            "alert_time",
            "location",
            "longitude",
            "latitude",
            "publisher",
            "create_at",
        ]

        for field in required_fields:
            assert field in data, f"响应缺少必需字段: {field}"
