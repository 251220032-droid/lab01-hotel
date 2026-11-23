"""预订订单服务。

对应 UML 类图业务服务模块中的 ``OrderService``，依赖
``InventoryService`` 与 ``TimeoutScheduler``。负责把检索到的
房型转化为订单：先做跨日校验与库存锁定，再按每日价格计算
总金额并生成待支付订单；同时处理用户取消、超时取消与突发
停业时的批量取消。
"""

from datetime import timedelta

from ..models import Order, OrderStatus


class OrderError(Exception):
    """订单相关业务异常。"""


class OrderService:
    """创建、取消订单并维护订单与库存的一致性。"""

    def __init__(self, database, inventory_service) -> None:
        self._database = database
        self._inventory = inventory_service

    @property
    def database(self):
        """关联数据库。"""
        return self._database

    @staticmethod
    def _date_range(check_in, check_out):
        """生成入住区间内的日期列表。"""
        days = (check_out - check_in).days
        return [check_in + timedelta(days=offset) for offset in range(days)]

    def calculate_amount(self, room_type_id: int, check_in, check_out,
                         quantity: int = 1) -> float:
        """按入住期间每日价格求和计算总金额。"""
        room_type = self._inventory.get_room_type(room_type_id)
        total = 0.0
        for target_date in self._date_range(check_in, check_out):
            inventory = room_type.get_inventory(target_date)
            if inventory is None:
                raise OrderError("存在未配置价格的日期")
            total += inventory.price * quantity
        return round(total, 2)

    def create_order(self, customer, room_type_id: int, check_in, check_out,
                     quantity: int = 1) -> Order:
        """校验并锁定库存后创建待支付订单。"""
        if not self._inventory.check_daily_availability(
                room_type_id, check_in, check_out, quantity):
            raise OrderError("所选日期内部分日期无房")
        if not self._inventory.lock_inventory(
                room_type_id, check_in, check_out, quantity):
            raise OrderError("该房型已无房或正在被他人预订")

        amount = self.calculate_amount(
            room_type_id, check_in, check_out, quantity)
        order_id = self._database.next_id("orders")
        order = Order(
            order_id, customer.user_id, room_type_id,
            self._inventory.get_room_type(room_type_id).hotel_id,
            check_in, check_out, amount, quantity,
        )
        self._database.add("orders", order)
        self._database.save()
        return order

    def cancel_order(self, order: Order) -> None:
        """顾客主动取消待支付订单并释放库存。"""
        if order.status != OrderStatus.PENDING_PAYMENT:
            raise OrderError("只有待支付订单可以取消")
        order.mark_cancelled()
        self._inventory.release_inventory(
            order.room_type_id, order.check_in_date,
            order.check_out_date, order.quantity,
        )
        self._database.save()

    def cancel_expired_order(self, order: Order) -> None:
        """超时取消：标记取消并释放库存（供 TimeoutScheduler 调用）。"""
        order.mark_cancelled()
        self._inventory.release_inventory(
            order.room_type_id, order.check_in_date,
            order.check_out_date, order.quantity,
        )
        self._database.save()

    def batch_cancel(self, hotel_id: int) -> list:
        """突发停业时批量取消某酒店全部未入住的有效订单。

        已确认与待支付订单都会被取消；待支付订单释放锁定库存，
        已确认订单交由支付服务退款。返回被取消的订单列表。
        """
        affected = []
        for order in list(self._database.collection("orders")):
            if order.hotel_id != hotel_id:
                continue
            if order.status in (OrderStatus.CONFIRMED, OrderStatus.PENDING_PAYMENT):
                if order.status == OrderStatus.PENDING_PAYMENT:
                    self._inventory.release_inventory(
                        order.room_type_id, order.check_in_date,
                        order.check_out_date, order.quantity,
                    )
                order.mark_cancelled()
                affected.append(order)
        self._database.save()
        return affected

    def orders_of_customer(self, customer_id: int) -> list:
        """返回某顾客的全部订单，按下单时间倒序。"""
        orders = [
            order for order in self._database.collection("orders")
            if order.customer_id == customer_id
        ]
        return sorted(orders, key=lambda item: item.created_at, reverse=True)
