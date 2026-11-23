"""前台核销服务的单元测试。"""

from datetime import timedelta

import pytest

from hotelapp.models import OrderStatus, PaymentMethod
from hotelapp.services.checkin_service import CheckInError


def _paid_order_for_today(context, customer, room_type, today):
    """构造一笔今日入住、已支付的订单。"""
    order = context.orders.create_order(
        customer, room_type.room_type_id, today, today + timedelta(days=2))
    context.payments.process_payment(order, PaymentMethod.ALIPAY)
    return order


def test_find_order_by_code(context, customer, room_type, today):
    """应能通过核销码定位订单。"""
    order = _paid_order_for_today(context, customer, room_type, today)
    assert context.checkin.find_order_by_code(order.check_code) is order
    assert context.checkin.find_order_by_code("000000") is None


def test_check_in_success(context, customer, room_type, today):
    """核销码正确、状态与日期满足时可办理入住。"""
    order = _paid_order_for_today(context, customer, room_type, today)
    record = context.checkin.handle_check_in(order, order.check_code)
    assert record.check_in_time is not None
    assert context.checkin.is_checked_in(order.order_id)


def test_check_in_wrong_code_rejected(context, customer, room_type, today):
    """核销码错误应拒绝办理。"""
    order = _paid_order_for_today(context, customer, room_type, today)
    with pytest.raises(CheckInError):
        context.checkin.handle_check_in(order, "wrong")


def test_check_in_unpaid_order_rejected(context, customer, room_type, today):
    """未支付的待支付订单不能核销。"""
    order = context.orders.create_order(
        customer, room_type.room_type_id, today, today + timedelta(days=2))
    with pytest.raises(CheckInError):
        context.checkin.handle_check_in(order, order.check_code)


def test_check_in_before_arrival_rejected(context, customer, room_type, today):
    """未到入住日期不能提前核销。"""
    future = today + timedelta(days=2)
    order = context.orders.create_order(
        customer, room_type.room_type_id, future, future + timedelta(days=1))
    context.payments.process_payment(order, PaymentMethod.ALIPAY)
    with pytest.raises(CheckInError):
        context.checkin.handle_check_in(order, order.check_code)


def test_duplicate_check_in_rejected(context, customer, room_type, today):
    """同一订单不能重复办理入住。"""
    order = _paid_order_for_today(context, customer, room_type, today)
    context.checkin.handle_check_in(order, order.check_code)
    with pytest.raises(CheckInError):
        context.checkin.handle_check_in(order, order.check_code)


def test_check_out_completes_order(context, customer, room_type, today):
    """退房后订单置为已完成并记录退房时间。"""
    order = _paid_order_for_today(context, customer, room_type, today)
    context.checkin.handle_check_in(order, order.check_code)
    record = context.checkin.handle_check_out(order)
    assert record.check_out_time is not None
    assert order.status == OrderStatus.COMPLETED


def test_check_out_without_check_in_rejected(context, customer, room_type, today):
    """未入住直接退房应拒绝。"""
    order = _paid_order_for_today(context, customer, room_type, today)
    with pytest.raises(CheckInError):
        context.checkin.handle_check_out(order)
