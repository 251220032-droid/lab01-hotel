"""订单支付模块的数据模型。

对应 UML 类图中的 ``Order``、``Payment`` 与枚举 ``OrderStatus``。
订单记录买家、房型、入住离店日期、金额、15 分钟支付截止时间，
以及用于线下核销的随机核销码；支付记录则保存支付方式与状态。
"""

from datetime import datetime, timedelta
import secrets

from .enums import OrderStatus, PaymentMethod

# 待支付订单的有效时长（分钟），对应 REQ-005/REQ-006。
PAYMENT_WINDOW_MINUTES = 15


class Order:
    """酒店预订订单，承载状态机与支付超时判断。"""

    def __init__(self, order_id: int, customer_id: int, room_type_id: int,
                 hotel_id: int, check_in_date, check_out_date,
                 total_amount: float, quantity: int = 1,
                 created_at: datetime = None,
                 status: OrderStatus = OrderStatus.PENDING_PAYMENT) -> None:
        self._order_id = order_id
        self._customer_id = customer_id
        self._room_type_id = room_type_id
        self._hotel_id = hotel_id
        self._check_in_date = check_in_date
        self._check_out_date = check_out_date
        self._quantity = quantity
        self._total_amount = total_amount
        self._status = status
        self._created_at = created_at or datetime.now()
        self._expire_at = self._created_at + timedelta(minutes=PAYMENT_WINDOW_MINUTES)
        # 6 位数字核销码，供前台扫码或手动输入。
        self._check_code = f"{secrets.randbelow(10 ** 6):06d}"

    @property
    def order_id(self) -> int:
        """订单唯一标识。"""
        return self._order_id

    @property
    def customer_id(self) -> int:
        """下单顾客标识。"""
        return self._customer_id

    @property
    def room_type_id(self) -> int:
        """预订房型标识。"""
        return self._room_type_id

    @property
    def hotel_id(self) -> int:
        """预订酒店标识。"""
        return self._hotel_id

    @property
    def check_in_date(self):
        """入住日期。"""
        return self._check_in_date

    @property
    def check_out_date(self):
        """离店日期。"""
        return self._check_out_date

    @property
    def quantity(self) -> int:
        """预订房间数量。"""
        return self._quantity

    @property
    def nights(self) -> int:
        """入住晚数，由离店与入住日期之差得到。"""
        return (self._check_out_date - self._check_in_date).days

    @property
    def total_amount(self) -> float:
        """订单总金额。"""
        return self._total_amount

    @property
    def status(self) -> OrderStatus:
        """订单当前状态。"""
        return self._status

    @property
    def created_at(self) -> datetime:
        """下单时间。"""
        return self._created_at

    @property
    def expire_at(self) -> datetime:
        """支付截止时间。"""
        return self._expire_at

    @property
    def check_code(self) -> str:
        """线下核销码。"""
        return self._check_code

    def is_expired(self, now: datetime = None) -> bool:
        """判断待支付订单是否已超过 15 分钟。"""
        current = now or datetime.now()
        return self._status == OrderStatus.PENDING_PAYMENT and current >= self._expire_at

    def can_pay(self, now: datetime = None) -> bool:
        """判断订单当前是否允许支付。"""
        current = now or datetime.now()
        return self._status == OrderStatus.PENDING_PAYMENT and current < self._expire_at

    def mark_confirmed(self) -> None:
        """支付成功后将订单置为已确认。"""
        if self._status != OrderStatus.PENDING_PAYMENT:
            raise RuntimeError("只有待支付订单才能确认")
        self._status = OrderStatus.CONFIRMED

    def mark_cancelled(self) -> None:
        """取消订单（超时或用户主动取消）。"""
        if self._status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
            raise RuntimeError("当前状态不允许取消")
        self._status = OrderStatus.CANCELLED

    def mark_completed(self) -> None:
        """核销退房完成后置为已完成。"""
        if self._status != OrderStatus.CONFIRMED:
            raise RuntimeError("只有已确认订单才能完成")
        self._status = OrderStatus.COMPLETED

    def to_dict(self) -> dict:
        """序列化订单。"""
        return {
            "order_id": self._order_id,
            "customer_id": self._customer_id,
            "room_type_id": self._room_type_id,
            "hotel_id": self._hotel_id,
            "check_in_date": self._check_in_date.isoformat(),
            "check_out_date": self._check_out_date.isoformat(),
            "quantity": self._quantity,
            "total_amount": self._total_amount,
            "status": self._status.name,
            "created_at": self._created_at.isoformat(timespec="seconds"),
            "expire_at": self._expire_at.isoformat(timespec="seconds"),
            "check_code": self._check_code,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Order":
        """根据字典重建订单，并恢复其状态与时间字段。"""
        # 局部导入以避免与模块名冲突，仅反序列化时使用。
        from datetime import date as date_type  # pylint: disable=import-outside-toplevel

        order = cls(
            order_id=data["order_id"],
            customer_id=data["customer_id"],
            room_type_id=data["room_type_id"],
            hotel_id=data["hotel_id"],
            check_in_date=date_type.fromisoformat(data["check_in_date"]),
            check_out_date=date_type.fromisoformat(data["check_out_date"]),
            total_amount=data["total_amount"],
            quantity=data.get("quantity", 1),
            created_at=datetime.fromisoformat(data["created_at"]),
            status=OrderStatus[data["status"]],
        )
        order._expire_at = datetime.fromisoformat(data["expire_at"])
        order._check_code = data["check_code"]
        return order


class Payment:
    """支付记录，保存支付方式、状态与支付时间，并支持退款标记。"""

    def __init__(self, payment_id: int, order_id: int, amount: float,
                 method: PaymentMethod, paid_at: datetime = None,
                 pay_status: str = "成功", refunded: bool = False) -> None:
        self._payment_id = payment_id
        self._order_id = order_id
        self._amount = amount
        self._method = method
        self._paid_at = paid_at or datetime.now()
        self._pay_status = pay_status
        self._refunded = refunded

    @property
    def payment_id(self) -> int:
        """支付记录标识。"""
        return self._payment_id

    @property
    def order_id(self) -> int:
        """关联订单标识。"""
        return self._order_id

    @property
    def amount(self) -> float:
        """支付金额。"""
        return self._amount

    @property
    def method(self) -> PaymentMethod:
        """支付方式。"""
        return self._method

    @property
    def paid_at(self) -> datetime:
        """支付完成时间。"""
        return self._paid_at

    @property
    def pay_status(self) -> str:
        """支付状态描述。"""
        return self._pay_status

    @property
    def refunded(self) -> bool:
        """是否已退款。"""
        return self._refunded

    def mark_refunded(self) -> None:
        """标记该笔支付已原路退回。"""
        self._refunded = True

    def to_dict(self) -> dict:
        """序列化支付记录。"""
        return {
            "payment_id": self._payment_id,
            "order_id": self._order_id,
            "amount": self._amount,
            "method": self._method.name,
            "paid_at": self._paid_at.isoformat(timespec="seconds"),
            "pay_status": self._pay_status,
            "refunded": self._refunded,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Payment":
        """根据字典重建支付记录。"""
        return cls(
            payment_id=data["payment_id"],
            order_id=data["order_id"],
            amount=data["amount"],
            method=PaymentMethod[data["method"]],
            paid_at=datetime.fromisoformat(data["paid_at"]),
            pay_status=data.get("pay_status", "成功"),
            refunded=data.get("refunded", False),
        )
