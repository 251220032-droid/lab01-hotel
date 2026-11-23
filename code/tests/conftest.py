"""pytest 共享夹具。

每个测试通过 ``tmp_path`` 获得独立的数据目录，因此
``ApplicationContext`` 之间互不影响，测试可重复运行。
"""

from datetime import date, timedelta

import pytest

from hotelapp.services.app_context import ApplicationContext


@pytest.fixture
def context(tmp_path):
    """在临时目录中初始化带演示数据的应用上下文。"""
    return ApplicationContext(base_dir=str(tmp_path))


@pytest.fixture
def customer(context):
    """返回演示顾客账号。"""
    return context.database.find_user_by_name("customer")


@pytest.fixture
def admin(context):
    """返回演示管理员账号。"""
    return context.database.find_user_by_name("admin")


@pytest.fixture
def room_type(context):
    """返回库存充足的高级大床房房型。"""
    return context.inventory.list_room_types()[0]


@pytest.fixture
def economy_room(context):
    """返回经济单人房房型（首日停售、库存为 0）。"""
    return context.inventory.list_room_types()[3]


@pytest.fixture
def today():
    """返回当前日期。"""
    return date.today()


@pytest.fixture
def future_window(today):
    """返回一组落在演示房态窗口内的入住、离店日期。"""
    return today + timedelta(days=1), today + timedelta(days=3)
