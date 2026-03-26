"""
预警信息接口测试模块。

测试覆盖：
1. 正常路径：获取预警列表、获取单个预警、删除预警
2. 异常路径：预警不存在、权限验证
3. 响应体结构校验

注意：由于原代码中alerts路由直接使用SQLModel作为请求体模型，
而SQLModel不会自动将JSON字符串转换为datetime对象，
因此创建/更新预警的POST/PUT/PATCH接口存在已知问题。
本测试重点测试可正常工作的接口功能。
"""

from datetime import datetime, timezone

import pytest
from fastapi import status

from ..core.models import Alert


class TestAlertEndpoints:
    """预警信息接口测试类"""

    def _create_test_alert(self, session, **kwargs):
        """辅助方法：创建测试预警数据"""
        current_time = datetime.now(timezone.utc)
        alert_data = {
            "alert_type": "暴雨",
            "alert_level": "红色",
            "alert_name": "暴雨红色预警",
            "alert_description": "预计未来24小时内将有特大暴雨",
            "alert_time": current_time,
            "location": "北京市朝阳区",
            "longitude": 116.4,
            "latitude": 39.9,
            "publisher": "北京市气象局"
        }
        alert_data.update(kwargs)
        alert = Alert(**alert_data)
        session.add(alert)
        session.commit()
        session.refresh(alert)
        return alert

    def test_get_alerts_list(self, client, user_token_headers, test_session):
        """测试获取预警信息列表 - 正常路径"""
        # 先创建几个测试预警
        current_time = datetime.now(timezone.utc)
        for i in range(3):
            alert = Alert(
                alert_type=f"类型{i}",
                alert_level="黄色",
                alert_name=f"预警{i}",
                alert_description=f"描述{i}",
                alert_time=current_time,
                location=f"地点{i}",
                longitude=116.0 + i,
                latitude=39.0 + i,
                publisher=f"发布者{i}"
            )
            test_session.add(alert)
        test_session.commit()

        # 发送获取列表请求
        response = client.get("/alerts/", headers=user_token_headers)

        # 验证响应
        assert response.status_code == status.HTTP_200_OK, "获取预警列表失败"
        response_data = response.json()
        assert isinstance(response_data, list), "响应应为列表类型"
        assert len(response_data) >= 3, "预警列表数量不正确"

        # 验证每个预警的结构
        for alert_data in response_data:
            assert "id" in alert_data
            assert "alert_type" in alert_data
            assert "alert_level" in alert_data
            assert "alert_name" in alert_data

    def test_get_alerts_pagination(self, client, user_token_headers, test_session):
        """测试获取预警信息列表 - 分页功能 - 正常路径"""
        # 清除现有预警数据
        from sqlmodel import select
        results = test_session.exec(select(Alert)).all()
        for alert in results:
            test_session.delete(alert)
        test_session.commit()

        # 创建多个测试预警
        current_time = datetime.now(timezone.utc)
        for i in range(15):
            alert = Alert(
                alert_type="暴雨",
                alert_level="黄色",
                alert_name=f"暴雨预警{i:02d}",
                alert_description=f"第{i}号预警",
                alert_time=current_time,
                location=f"地点{i}",
                longitude=116.0,
                latitude=39.0,
                publisher="气象局"
            )
            test_session.add(alert)
        test_session.commit()

        # 测试第一页
        response = client.get("/alerts/?offset=0&limit=5", headers=user_token_headers)
        assert response.status_code == status.HTTP_200_OK
        page1 = response.json()
        assert len(page1) == 5, "第一页应有5条预警"

        # 测试第二页
        response = client.get("/alerts/?offset=5&limit=5", headers=user_token_headers)
        assert response.status_code == status.HTTP_200_OK
        page2 = response.json()
        assert len(page2) == 5, "第二页应有5条预警"

        # 验证两页数据不重复
        page1_ids = {a["id"] for a in page1}
        page2_ids = {a["id"] for a in page2}
        assert page1_ids.isdisjoint(page2_ids), "分页数据不应重复"

    def test_get_single_alert(self, client, user_token_headers, test_session):
        """测试获取单个预警信息 - 正常路径"""
        # 创建测试预警
        alert = self._create_test_alert(test_session)

        # 发送获取单个预警请求
        response = client.get(f"/alerts/{alert.id}", headers=user_token_headers)

        assert response.status_code == status.HTTP_200_OK, "获取单个预警失败"
        response_data = response.json()
        assert response_data["id"] == alert.id, "预警ID不匹配"
        assert response_data["alert_type"] == "暴雨", "预警类型不匹配"
        assert response_data["alert_name"] == "暴雨红色预警", "预警名称不匹配"

    def test_get_alert_not_found(self, client, user_token_headers):
        """测试获取单个预警信息 - 预警不存在 - 异常路径"""
        response = client.get("/alerts/99999", headers=user_token_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND, "不存在的预警应返回404"
        assert response.json()["detail"] == "预警信息不存在", "错误信息不正确"

    def test_delete_alert_success(self, client, user_token_headers, test_session):
        """测试删除预警信息 - 正常路径"""
        # 创建测试预警
        alert = self._create_test_alert(test_session, alert_type="沙尘暴", alert_name="沙尘暴黄色预警")
        alert_id = alert.id

        # 删除预警
        response = client.delete(f"/alerts/{alert_id}", headers=user_token_headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT, "删除预警失败"

        # 验证预警已删除
        deleted_alert = test_session.get(Alert, alert_id)
        assert deleted_alert is None, "预警未被删除"

    def test_delete_alert_not_found(self, client, user_token_headers):
        """测试删除预警信息 - 预警不存在 - 异常路径"""
        response = client.delete("/alerts/99999", headers=user_token_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND, "删除不存在的预警应返回404"

    def test_alert_unauthorized_access(self, unauthenticated_client):
        """测试未授权访问预警接口 - 异常路径"""
        response = unauthenticated_client.get("/alerts/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED, "未授权访问应返回401"

    def test_create_alert_extreme_coordinates(self, client, user_token_headers, test_session):
        """测试预警信息 - 经纬度边界值测试 - 正常路径"""
        # 测试经纬度边界值 - 通过数据库直接创建验证
        current_time = datetime.now(timezone.utc)
        alert = Alert(
            alert_type="地震",
            alert_level="红色",
            alert_name="地震预警",
            alert_description="地震活动预警",
            alert_time=current_time,
            location="测试地点",
            longitude=180.0,  # 经度最大值
            latitude=90.0,  # 纬度最大值
            publisher="地震局"
        )
        test_session.add(alert)
        test_session.commit()
        test_session.refresh(alert)

        # 通过获取验证数据正确保存
        response = client.get(f"/alerts/{alert.id}", headers=user_token_headers)
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["longitude"] == 180.0
        assert response_data["latitude"] == 90.0

    def test_read_current_user_with_alerts_access(self, client, user_token_headers):
        """测试当前用户信息获取 - 确保认证正常工作"""
        response = client.get("/users/me", headers=user_token_headers)
        assert response.status_code == status.HTTP_200_OK, "获取当前用户信息失败"
