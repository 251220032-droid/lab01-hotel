"""支付与退款服务。

对应 UML 类图业务服务模块中的 ``PaymentService``，依赖
``Payment`` 与 ``ExceptionLog``。本模块通过一个可注入故障的
网关模拟类，演示支付/退款调用、网关异常捕获、异常日志记录
与人工重试（REQ-011、REQ-010）。
"""

from datetime import datetime

from ..models import Payment, PaymentMethod, OrderStatus


class PaymentError(Exception):
    """支付相关业务异常。"""


class PaymentGateway:
    """第三方支付网关的本地模拟，可预置故障以测试异常分支。"""

    def __init__(self) -> None:
        self._fail_next = False

    def set_fault(self, fail: bool) -> None:
        """设置下一次调用是否模拟网关超时/失败。"""
        self._fail_next = fail

    def charge(self, amount: float) -> bool:
        """发起扣款，返回是否成功。"""
        if self._fail_next:
            self._fail_next = False
            return False
        return amount >= 0

    def refund(self, amount: float) -> bool:
        """发起原路退款，返回是否成功。"""
        if self._fail_next:
            self._fail_next = False
            return False
        return amount >= 0


class PaymentService:
    """处理支付、退款与网关异常日志。"""

    def __init__(self, database, log_manager, gateway: PaymentGateway = None) -> None:
        self._database = database
        self._log_manager = log_manager
        self._gateway = gateway or PaymentGateway()

    @property
    def gateway(self) -> PaymentGateway:
        """网关模拟对象，可用于测试时注入故障。"""
        return self._gateway

    def process_payment(self, order, method: PaymentMethod) -> Payment:
        """对待支付订单发起支付，成功后确认订单。"""
        if not order.can_pay():
            raise PaymentError("订单已超时或不可支付")
        if not self._gateway.charge(order.total_amount):
            raise PaymentError("支付网关响应超时，请稍后重试")
        payment_id = self._database.next_id("payments")
        payment = Payment(
            payment_id, order.order_id, order.total_amount, method,
        )
        self._database.add("payments", payment)
        order.mark_confirmed()
        self._database.save()
        return payment

    def find_payment(self, order_id: int) -> Payment:
        """查找订单对应的支付记录。"""
        for payment in self._database.collection("payments"):
            if payment.order_id == order_id:
                return payment
        return None

    def refund(self, order) -> Payment:
        """对已确认订单原路退款；网关失败时记录异常日志并标记待重试。"""
        if order.status != OrderStatus.CANCELLED:
            raise PaymentError("只能对已取消订单退款")
        payment = self.find_payment(order.order_id)
        if payment is None:
            raise PaymentError("未找到支付记录")
        if not self._gateway.refund(payment.amount):
            self._log_manager.add(
                "退款网关超时",
                f"订单 {order.order_id}，金额 {payment.amount}",
            )
            self._database.save()
            raise PaymentError("退款失败，已记录异常并标记待人工重试")
        payment.mark_refunded()
        self._database.save()
        return payment

    def retry_refund(self, order) -> Payment:
        """人工重试退款，成功后把对应异常日志标记为已处理。"""
        payment = self.refund(order)
        for log in self._log_manager.pending_logs():
            if str(order.order_id) in log.context:
                self._log_manager.resolve(log.log_id)
        return payment

    @staticmethod
    def now() -> datetime:
        """返回当前时间，便于统一时间口径。"""
        return datetime.now()
