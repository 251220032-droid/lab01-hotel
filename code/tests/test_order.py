"""订单服务的单元测试。"""

from datetime import timedelta

import pytest

from hotelapp.models import OrderStatus
from hotelapp.services.order_service import OrderError


def test_calculate_amount_sums_daily_prices(context, room_type, future_window):
    """总金额应等于入住期间每日房价之和。"""
    check_in, check_out = future_window
    expected = sum(
        room_type.get_inventory(check_in + timedelta(days=i)).price
        for i in range(2))
    amount = context.orders.calculate_amount(
        room_type.room_type_id, check_in, check_out)
    assert amount == round(expected, 2)


def test_create_order_locks_stock(context, customer, room_type, future_window):
    """下单后订单为待支付状态，且对应库存已扣减。"""
    check_in, check_out = future_window
    room_id = room_type.room_type_id
    order = context.orders.create_order(
        customer, room_id, check_in, check_out)
    assert order.status == OrderStatus.PENDING_PAYMENT
    assert order.nights == 2
    assert not room_type.is_available(
        check_in, quantity=room_type.get_inventory(check_in).available_count + 1)


def test_create_order_without_availability_raises(context, customer,
                                                  economy_room, today):
    """对停售无房日期下单应抛出订单异常。"""
    with pytest.raises(OrderError):
        context.orders.create_order(
            customer, economy_room.room_type_id,
            today, today + timedelta(days=1))


def test_cancel_order_releases_stock(context, customer, room_type, future_window):
    """主动取消待支付订单后库存恢复。"""
    check_in, check_out = future_window
    order = context.orders.create_order(
        customer, room_type.room_type_id, check_in, check_out)
    count_after_lock = room_type.get_inventory(check_in).available_count
    context.orders.cancel_order(order)
    assert order.status == OrderStatus.CANCELLED
    assert room_type.get_inventory(check_in).available_count == (
        count_after_lock + 1)


def test_cancel_confirmed_order_rejected(context, customer, room_type,
                                         future_window):
    """非待支付订单不允许走普通取消。"""
    check_in, check_out = future_window
    order = context.orders.create_order(
        customer, room_type.room_type_id, check_in, check_out)
    order.mark_cancelled()
    with pytest.raises(OrderError):
        context.orders.cancel_order(order)


def test_batch_cancel_for_hotel(context, customer, room_type, future_window):
    """突发停业批量取消应命中该酒店全部有效订单。"""
    check_in, check_out = future_window
    order = context.orders.create_order(
        customer, room_type.room_type_id, check_in, check_out)
    affected = context.orders.batch_cancel(room_type.hotel_id)
    assert order in affected
    assert order.status == OrderStatus.CANCELLED


def test_orders_of_customer_sorted(context, customer, room_type, future_window):
    """应能按顾客查询订单且按下单时间倒序。"""
    check_in, check_out = future_window
    context.orders.create_order(
        customer, room_type.room_type_id, check_in, check_out)
    orders = context.orders.orders_of_customer(customer.user_id)
    assert len(orders) == 1
    assert orders[0].customer_id == customer.user_id
