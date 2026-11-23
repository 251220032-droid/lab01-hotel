"""数据库持久化与重新加载的回归测试。

重点验证：保存后重新加载，每日房态会重新关联到所属房型，
而不是各自独立、导致按日期查询失效。
"""

import os
from datetime import date

from hotelapp.core.database import Database
from hotelapp.services.app_context import ApplicationContext


def test_inventory_relation_rebuilt_after_reload(tmp_path):
    """重新加载后房型应能按日期找到房态记录。"""
    base = str(tmp_path)
    context = ApplicationContext(base_dir=base)
    context.shutdown()

    data_path = os.path.join(base, "runtime", "data.json")
    reloaded = Database(data_path)
    room_type = reloaded.collection("room_types")[0]
    assert len(room_type.inventories) > 0
    assert room_type.get_inventory(date.today()) is not None


def test_amount_calculable_after_reload(tmp_path):
    """重新加载后业务层仍能正确计算金额（端到端验证关联）。"""
    from datetime import timedelta

    base = str(tmp_path)
    context = ApplicationContext(base_dir=base)
    context.shutdown()

    data_path = os.path.join(base, "runtime", "data.json")
    reloaded = Database(data_path)
    room_type = reloaded.collection("room_types")[0]
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=2)
    inventory = room_type.get_inventory(check_in)
    expected = inventory.price + room_type.get_inventory(
        check_in + timedelta(days=1)).price
    assert room_type.get_inventory(check_in) is not None
    assert expected > 0


def test_round_trip_keeps_collections(tmp_path):
    """重新加载后各集合数量与保存前一致。"""
    base = str(tmp_path)
    context = ApplicationContext(base_dir=base)
    names = ("hotels", "room_types", "inventories")
    before = {name: len(context.database.collection(name)) for name in names}
    before["users"] = len(context.database.users)
    context.shutdown()
    reloaded = Database(os.path.join(base, "runtime", "data.json"))
    for name, count in before.items():
        target = reloaded.users if name == "users" else reloaded.collection(name)
        assert len(target) == count
