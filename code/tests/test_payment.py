"""支付与退款服务的单元测试。"""

from datetime import timedelta

import pytest

from hotelapp.models import OrderStatus, PaymentMethod
from hotelapp.services.order_service import OrderError
from hotelapp.services.payment_service import PaymentError


def _make_paid_order(context, customer, room_type, check_in, check_out):
    """构造一笔已支付确认的订单。"""
    order = context.orders.create_order(
        customer, room_type.room_type_id, check_in, check_out)
    context.payments.process_payment(order, PaymentMethod.ALIPAY)
    return order


def test_payment_success_confirms_order(context, customer, room_type,
                                        future_window):
    """支付成功后订单确认，且生成支付记录。"""
    check_in, check_out = future_window
    order = _make_paid_order(context, customer, room_type, check_in, check_out)
    assert order.status == OrderStatus.CONFIRMED
    payment = context.payments.find_payment(order.order_id)
    assert payment is not None
    assert payment.amount == order.total_amount


def test_payment_gateway_failure_keeps_pending(context, customer, room_type,
                                               future_window):
    """网关故障时支付抛错，订单保持待支付，可再次尝试。"""
    check_in, check_out = future_window
    order = context.orders.create_order(
        customer, room_type.room_type_id, check_in, check_out)
    context.payments.gateway.set_fault(True)
    with pytest.raises(PaymentError):
        context.payments.process_payment(order, PaymentMethod.WECHAT)
    assert order.status == OrderStatus.PENDING_PAYMENT
    # 故障为一次性，再次支付应成功。
    context.payments.process_payment(order, PaymentMethod.WECHAT)
    assert order.status == OrderStatus.CONFIRMED


def test_pay_expired_order_rejected(context, customer, room_type, future_window):
    """已超时订单不允许支付。"""
    check_in, check_out = future_window
    order = context.orders.create_order(
        customer, room_type.room_type_id, check_in, check_out)
    order._expire_at = order.created_at - timedelta(minutes=1)
    with pytest.raises(PaymentError):
        context.payments.process_payment(order, PaymentMethod.ALIPAY)


def test_refund_success(context, customer, room_type, future_window):
    """已取消的已支付订单可原路退款。"""
    check_in, check_out = future_window
    order = _make_paid_order(context, customer, room_type, check_in, check_out)
    order.mark_cancelled()
    payment = context.payments.refund(order)
    assert payment.refunded


def test_refund_gateway_failure_logs_and_raises(context, customer, room_type,
                                                 future_window):
    """退款网关失败应记录异常日志并抛出，等待人工重试。"""
    check_in, check_out = future_window
    order = _make_paid_order(context, customer, room_type, check_in, check_out)
    order.mark_cancelled()
    context.payments.gateway.set_fault(True)
    with pytest.raises(PaymentError):
        context.payments.refund(order)
    assert context.log_manager.pending_logs()


def test_retry_refund_resolves_log(context, customer, room_type, future_window):
    """人工重试退款成功后，对应异常日志被处理。"""
    check_in, check_out = future_window
    order = _make_paid_order(context, customer, room_type, check_in, check_out)
    order.mark_cancelled()
    context.payments.gateway.set_fault(True)
    with pytest.raises(PaymentError):
        context.payments.refund(order)
    payment = context.payments.retry_refund(order)
    assert payment.refunded
    assert not context.log_manager.pending_logs()


def test_refund_without_payment_rejected(context, customer, room_type,
                                         future_window):
    """未支付订单直接退款应抛错。"""
    check_in, check_out = future_window
    order = context.orders.create_order(
        customer, room_type.room_type_id, check_in, check_out)
    order.mark_cancelled()
    with pytest.raises(PaymentError):
        context.payments.refund(order)
