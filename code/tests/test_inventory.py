"""库存服务的单元测试。"""

from datetime import timedelta

import pytest

from hotelapp.models import RoomStatus
from hotelapp.services.inventory_service import InventoryError


def test_daily_availability_ok(context, room_type, future_window):
    """库存充足的日期区间应通过逐日校验。"""
    check_in, check_out = future_window
    assert context.inventory.check_daily_availability(
        room_type.room_type_id, check_in, check_out)


def test_stopped_first_day_unavailable(context, economy_room, today):
    """经济单人房首日停售且库存为 0，应判定不可用。"""
    inventory = economy_room.get_inventory(today)
    assert inventory.status == RoomStatus.STOPPED
    assert not economy_room.is_available(today)


def test_date_range_requires_checkout_after_checkin(context, room_type, today):
    """离店不晚于入住应抛出业务异常。"""
    with pytest.raises(InventoryError):
        context.inventory.check_daily_availability(
            room_type.room_type_id, today, today)


def test_lock_decreases_and_release_restores(context, room_type, future_window):
    """锁定后每日库存扣减，释放后恢复。"""
    check_in, check_out = future_window
    room_id = room_type.room_type_id
    before = [room_type.get_inventory(
        check_in + timedelta(days=i)).available_count for i in range(2)]
    assert context.inventory.lock_inventory(room_id, check_in, check_out)
    locked = [room_type.get_inventory(
        check_in + timedelta(days=i)).available_count for i in range(2)]
    assert locked == [value - 1 for value in before]
    context.inventory.release_inventory(room_id, check_in, check_out)
    after = [room_type.get_inventory(
        check_in + timedelta(days=i)).available_count for i in range(2)]
    assert after == before


def test_lock_fails_when_quantity_exceeds_stock(context, room_type, future_window):
    """预订数量超过库存应锁定失败。"""
    check_in, check_out = future_window
    assert not context.inventory.lock_inventory(
        room_type.room_type_id, check_in, check_out, quantity=99)


def test_lock_fails_on_stopped_day(context, economy_room, today):
    """对停售日期加锁应失败。"""
    check_out = today + timedelta(days=1)
    assert not context.inventory.lock_inventory(
        economy_room.room_type_id, today, check_out)


def test_get_unknown_room_type_raises(context):
    """获取不存在的房型应抛异常。"""
    with pytest.raises(InventoryError):
        context.inventory.get_room_type(9999)


def test_upsert_inventory_and_negative_guard(context, room_type, today):
    """新增房态可更新库存与价格，负数被拒绝。"""
    target = today + timedelta(days=10)
    record = context.inventory.upsert_inventory(
        room_type.room_type_id, target, 5, 400)
    assert record.available_count == 5
    assert record.price == 400
    with pytest.raises(InventoryError):
        context.inventory.upsert_inventory(room_type.room_type_id, target, -1, 100)


def test_set_sale_status(context, room_type, future_window):
    """可将某日期停售再恢复。"""
    check_in, _ = future_window
    room_id = room_type.room_type_id
    context.inventory.set_sale_status(room_id, check_in, stop=True)
    assert room_type.get_inventory(check_in).status == RoomStatus.STOPPED
    context.inventory.set_sale_status(room_id, check_in, stop=False)
    assert room_type.get_inventory(check_in).status == RoomStatus.ON_SALE
