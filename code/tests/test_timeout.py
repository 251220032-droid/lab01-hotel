"""超时调度组件的单元测试。"""

from datetime import datetime, timedelta

from hotelapp.core import TimeoutScheduler
from hotelapp.models import OrderStatus


def test_find_expired_orders(context, customer, room_type, future_window):
    """超过支付窗口仍待支付的订单应被识别。"""
    check_in, check_out = future_window
    order = context.orders.create_order(
        customer, room_type.room_type_id, check_in, check_out)
    assert not TimeoutScheduler.find_expired_orders(
        context.database.collection("orders"))
    order._expire_at = datetime.now() - timedelta(minutes=1)
    expired = TimeoutScheduler.find_expired_orders(
        context.database.collection("orders"))
    assert order in expired


def test_auto_cancel_releases_stock(context, customer, room_type, future_window):
    """自动取消应标记取消并释放锁定库存。"""
    check_in, check_out = future_window
    order = context.orders.create_order(
        customer, room_type.room_type_id, check_in, check_out)
    locked_count = room_type.get_inventory(check_in).available_count
    order._expire_at = datetime.now() - timedelta(minutes=1)
    cancelled = TimeoutScheduler.auto_cancel(context.orders)
    assert order in cancelled
    assert order.status == OrderStatus.CANCELLED
    assert room_type.get_inventory(check_in).available_count == (
        locked_count + 1)


def test_remaining_seconds_countdown(context, customer, room_type, future_window):
    """剩余支付秒数应在窗口内为正，超时后归零。"""
    check_in, check_out = future_window
    order = context.orders.create_order(
        customer, room_type.room_type_id, check_in, check_out)
    assert TimeoutScheduler.remaining_seconds(order) > 0
    order._expire_at = datetime.now() - timedelta(seconds=5)
    assert TimeoutScheduler.remaining_seconds(order) == 0
