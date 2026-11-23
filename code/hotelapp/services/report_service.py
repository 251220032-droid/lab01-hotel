"""经营报表服务。

对应 UML 类图业务服务模块中的 ``ReportService``，依赖
``Order`` 统计经营数据（REQ-012）。提供订单总数、入住率、
营业额、取消率，以及房型订单占比与营业额趋势，供管理员
界面展示。
"""

from collections import defaultdict

from ..models import OrderStatus


class ReportService:
    """根据订单与房型数据计算经营指标。"""

    def __init__(self, database) -> None:
        self._database = database

    @property
    def database(self):
        """关联数据库。"""
        return self._database

    def _filter_orders(self, hotel_id=None, start=None, end=None) -> list:
        """按门店与时间范围过滤订单。"""
        result = self._database.collection("orders")
        if hotel_id is not None:
            result = [o for o in result if o.hotel_id == hotel_id]
        if start is not None:
            result = [o for o in result if o.check_in_date >= start]
        if end is not None:
            result = [o for o in result if o.check_in_date <= end]
        return result

    def order_count(self, **kwargs) -> int:
        """统计订单总数。"""
        return len(self._filter_orders(**kwargs))

    def revenue(self, **kwargs) -> float:
        """统计已确认与已完成订单的营业额。"""
        valid = (OrderStatus.CONFIRMED, OrderStatus.COMPLETED)
        orders = [o for o in self._filter_orders(**kwargs) if o.status in valid]
        return round(sum(o.total_amount for o in orders), 2)

    def cancel_rate(self, **kwargs) -> float:
        """计算取消订单占比，无订单时返回 0。"""
        orders = self._filter_orders(**kwargs)
        if not orders:
            return 0.0
        cancelled = [o for o in orders if o.status == OrderStatus.CANCELLED]
        return round(len(cancelled) / len(orders) * 100, 1)

    def occupancy_rate(self, **kwargs) -> float:
        """根据已入住晚数与可售晚数估算入住率（百分比）。"""
        orders = [
            o for o in self._filter_orders(**kwargs)
            if o.status in (OrderStatus.CONFIRMED, OrderStatus.COMPLETED)
        ]
        booked_nights = sum(o.nights * o.quantity for o in orders)
        total_nights = self._sellable_nights(kwargs.get("hotel_id"))
        if total_nights == 0:
            return 0.0
        return round(min(booked_nights / total_nights, 1.0) * 100, 1)

    def _sellable_nights(self, hotel_id) -> int:
        """统计全部房态记录中的可售房晚数。"""
        total = 0
        for inventory in self._database.collection("inventories"):
            if hotel_id is None:
                total += inventory.available_count
        return total

    def room_type_share(self, **kwargs) -> dict:
        """计算各房型的订单占比（百分比）。"""
        counter = defaultdict(int)
        orders = self._filter_orders(**kwargs)
        for order in orders:
            counter[order.room_type_id] += 1
        total = sum(counter.values())
        if total == 0:
            return {}
        return {
            room_id: round(count / total * 100, 1)
            for room_id, count in counter.items()
        }

    def revenue_trend(self, points: int = 6, **kwargs) -> list:
        """按订单分组返回营业额趋势的数值序列。"""
        orders = [
            o for o in self._filter_orders(**kwargs)
            if o.status in (OrderStatus.CONFIRMED, OrderStatus.COMPLETED)
        ]
        orders.sort(key=lambda o: o.check_in_date)
        if not orders:
            return [0] * points
        buckets = defaultdict(float)
        for order in orders:
            buckets[order.check_in_date] += order.total_amount
        values = list(buckets.values())
        if len(values) >= points:
            return [round(v, 2) for v in values[-points:]]
        padding = [0] * (points - len(values))
        return padding + [round(v, 2) for v in values]

    def summary(self, **kwargs) -> dict:
        """一次性返回四个核心指标，便于界面调用。"""
        return {
            "order_count": self.order_count(**kwargs),
            "occupancy_rate": self.occupancy_rate(**kwargs),
            "revenue": self.revenue(**kwargs),
            "cancel_rate": self.cancel_rate(**kwargs),
        }
