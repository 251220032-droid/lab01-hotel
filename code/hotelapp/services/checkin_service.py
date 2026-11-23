"""前台核销服务。

对应 UML 类图业务服务模块中的 ``CheckInService``，依赖
``Order``。前台通过核销码办理入住与退房（REQ-009）：只有已
确认（已支付）且到达入住日期的订单才能核销，未支付或已取消
订单将被拒绝；退房后订单置为已完成。
"""

from datetime import datetime, date

from ..models import OrderStatus


class CheckInError(Exception):
    """核销相关业务异常。"""


class CheckInRecord:
    """一次入住的核销记录，保存入住与退房时间。"""

    def __init__(self, order_id: int, check_in_time: datetime) -> None:
        self._order_id = order_id
        self._check_in_time = check_in_time
        self._check_out_time = None

    @property
    def order_id(self) -> int:
        """关联订单标识。"""
        return self._order_id

    @property
    def check_in_time(self) -> datetime:
        """入住时间。"""
        return self._check_in_time

    @property
    def check_out_time(self):
        """退房时间，未退房为 None。"""
        return self._check_out_time

    def check_out(self, when: datetime) -> None:
        """记录退房时间。"""
        self._check_out_time = when


class CheckInService:
    """核销码校验、入住与退房办理。"""

    def __init__(self, database) -> None:
        self._database = database
        self._records = {}

    @property
    def database(self):
        """关联数据库。"""
        return self._database

    def find_order_by_code(self, code: str):
        """按核销码查找订单，未找到返回 None。"""
        for order in self._database.collection("orders"):
            if order.check_code == code:
                return order
        return None

    def verify_code(self, order, code: str) -> bool:
        """校验核销码是否匹配。"""
        return order is not None and order.check_code == code

    def pending_checkin_orders(self) -> list:
        """返回当前可办理入住的已确认订单。"""
        return [
            order for order in self._database.collection("orders")
            if order.status == OrderStatus.CONFIRMED
        ]

    def handle_check_in(self, order, code: str) -> CheckInRecord:
        """办理入住，校验核销码、状态与入住日期。"""
        if not self.verify_code(order, code):
            raise CheckInError("核销码不正确")
        if order.status != OrderStatus.CONFIRMED:
            raise CheckInError("订单未支付或已取消，无法核销")
        if date.today() < order.check_in_date:
            raise CheckInError("尚未到达入住日期")
        if order.order_id in self._records:
            raise CheckInError("该订单已办理入住")
        record = CheckInRecord(order.order_id, datetime.now())
        self._records[order.order_id] = record
        return record

    def handle_check_out(self, order) -> CheckInRecord:
        """办理退房，订单置为已完成。"""
        record = self._records.get(order.order_id)
        if record is None:
            raise CheckInError("该订单尚未办理入住")
        if record.check_out_time is not None:
            raise CheckInError("该订单已退房")
        record.check_out(datetime.now())
        order.mark_completed()
        self._database.save()
        return record

    def is_checked_in(self, order_id: int) -> bool:
        """判断订单是否已办理入住。"""
        return order_id in self._records
