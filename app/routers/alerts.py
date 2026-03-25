"""预警信息路由模块。

提供预警信息的CRUD操作API端点。
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select

from ..core.db import SessionDep
from ..core.models import Alert, User
from ..dependencies import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
    dependencies=[Depends(get_current_active_user)],
)

ALERT_NOT_FOUND = "预警信息不存在"

CurrentUser = Annotated[User, Depends(get_current_active_user)]


def _apply_alert_update(alert: Alert, alert_update: Alert, exclude_unset: bool) -> None:
    """应用预警信息更新。

    Args:
        alert: 要更新的预警对象
        alert_update: 包含更新数据的预警对象
        exclude_unset: 是否排除未设置的字段
    """
    alert_data = alert_update.model_dump(exclude_unset=exclude_unset)
    for key, value in alert_data.items():
        setattr(alert, key, value)


@router.post("/", response_model=Alert, status_code=status.HTTP_201_CREATED)
def create_alert(
    alert: Alert,
    session: SessionDep,
    current_user: CurrentUser,
) -> Alert:
    """创建新的预警信息。

    Args:
        alert: 预警信息数据
        session: 数据库会话依赖
        current_user: 当前认证用户

    Returns:
        创建的预警信息对象
    """
    session.add(alert)
    session.commit()
    session.refresh(alert)
    logger.info(f"User {current_user.username} created alert: {alert!r}")
    return alert


@router.get("/", response_model=list[Alert])
def read_alerts(
    session: SessionDep,
    current_user: CurrentUser,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
) -> list[Alert]:
    """获取预警信息列表。

    Args:
        session: 数据库会话依赖
        current_user: 当前认证用户
        offset: 分页偏移量
        limit: 每页数量，最大100

    Returns:
        预警信息列表
    """
    statement = select(Alert).offset(offset).limit(limit)
    alerts = session.exec(statement).all()
    return list(alerts)


@router.get("/{alert_id}", response_model=Alert)
def read_alert(
    alert_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Alert:
    """获取单个预警信息。

    Args:
        alert_id: 预警信息ID
        session: 数据库会话依赖
        current_user: 当前认证用户

    Returns:
        预警信息对象

    Raises:
        HTTPException: 预警信息不存在时返回404
    """
    alert = session.get(Alert, alert_id)
    if not alert:
        logger.warning(f"Alert not found: id={alert_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ALERT_NOT_FOUND)
    return alert


@router.put("/{alert_id}", response_model=Alert)
def update_alert(
    alert_id: int,
    alert_update: Alert,
    session: SessionDep,
    current_user: CurrentUser,
) -> Alert:
    """完全更新预警信息。

    Args:
        alert_id: 预警信息ID
        alert_update: 更新的预警数据
        session: 数据库会话依赖
        current_user: 当前认证用户

    Returns:
        更新后的预警信息对象

    Raises:
        HTTPException: 预警信息不存在时返回404
    """
    alert = session.get(Alert, alert_id)
    if not alert:
        logger.warning(f"Alert not found for update: id={alert_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ALERT_NOT_FOUND)

    _apply_alert_update(alert, alert_update, exclude_unset=False)
    session.add(alert)
    session.commit()
    session.refresh(alert)
    logger.info(f"User {current_user.username} updated alert: {alert!r}")
    return alert


@router.patch("/{alert_id}", response_model=Alert)
def partial_update_alert(
    alert_id: int,
    alert_update: Alert,
    session: SessionDep,
    current_user: CurrentUser,
) -> Alert:
    """部分更新预警信息。

    Args:
        alert_id: 预警信息ID
        alert_update: 部分更新的预警数据
        session: 数据库会话依赖
        current_user: 当前认证用户

    Returns:
        更新后的预警信息对象

    Raises:
        HTTPException: 预警信息不存在时返回404
    """
    alert = session.get(Alert, alert_id)
    if not alert:
        logger.warning(f"Alert not found for partial update: id={alert_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ALERT_NOT_FOUND)

    _apply_alert_update(alert, alert_update, exclude_unset=True)
    session.add(alert)
    session.commit()
    session.refresh(alert)
    logger.info(f"User {current_user.username} partially updated alert: {alert!r}")
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    """删除预警信息。

    Args:
        alert_id: 预警信息ID
        session: 数据库会话依赖
        current_user: 当前认证用户

    Raises:
        HTTPException: 预警信息不存在时返回404
    """
    alert = session.get(Alert, alert_id)
    if not alert:
        logger.warning(f"Alert not found for deletion: id={alert_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ALERT_NOT_FOUND)
    session.delete(alert)
    session.commit()
    logger.info(f"User {current_user.username} deleted alert: id={alert_id}")
