"""经营报表服务的单元测试。"""

from hotelapp.models import PaymentMethod


def test_empty_report_initial(context):
    """没有订单时各项指标应为零或空。"""
    summary = context.reports.summary()
    assert summary["order_count"] == 0
    assert summary["revenue"] == 0
    assert summary["cancel_rate"] == 0
    assert context.reports.room_type_share() == {}


def test_report_after_paid_order(context, customer, room_type, future_window):
    """支付确认后订单数、营业额与占比应正确反映。"""
    check_in, check_out = future_window
    order = context.orders.create_order(
        customer, room_type.room_type_id, check_in, check_out)
    context.payments.process_payment(order, PaymentMethod.ALIPAY)
    summary = context.reports.summary()
    assert summary["order_count"] == 1
    assert summary["revenue"] == order.total_amount
    share = context.reports.room_type_share()
    assert share.get(room_type.room_type_id) == 100.0
    trend = context.reports.revenue_trend()
    assert order.total_amount in trend


def test_cancel_rate_after_cancellation(context, customer, room_type,
                                        future_window):
    """取消订单后取消率应为 100%。"""
    check_in, check_out = future_window
    order = context.orders.create_order(
        customer, room_type.room_type_id, check_in, check_out)
    context.orders.cancel_order(order)
    assert context.reports.cancel_rate() == 100.0


def test_revenue_excludes_unpaid_and_cancelled(context, customer, room_type,
                                                future_window):
    """待支付与已取消订单不计入营业额。"""
    check_in, check_out = future_window
    order = context.orders.create_order(
        customer, room_type.room_type_id, check_in, check_out)
    assert context.reports.revenue() == 0
    context.orders.cancel_order(order)
    assert context.reports.revenue() == 0
