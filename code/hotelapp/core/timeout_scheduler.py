"""超时调度组件。

对应 UML 类图业务服务模块中的 ``TimeoutScheduler``。订单创建后
若 15 分钟内未支付（REQ-006），系统需要自动取消并释放库存。
本组件提供两类能力：

- ``find_expired_orders`` 从订单集合中识别已超时的待支付订单；
- ``auto_cancel`` 借助订单服务完成取消与库存释放。

通过把订单服务作为方法参数注入，避免与服务层产生循环导入。
"""

from datetime import datetime

from ..models import OrderStatus


class TimeoutScheduler:
    """扫描待支付订单并处理超时取消。"""

    @staticmethod
    def find_expired_orders(orders, now: datetime = None) -> list:
        """返回所有已经超时但仍处于待支付状态的订单。"""
        current = now or datetime.now()
        return [
            order for order in orders
            if order.status == OrderStatus.PENDING_PAYMENT and order.is_expired(current)
        ]

    @staticmethod
    def auto_cancel(order_service, now: datetime = None) -> list:
        """对全部超时订单执行取消并释放库存，返回被取消的订单列表。"""
        current = now or datetime.now()
        expired = TimeoutScheduler.find_expired_orders(
            order_service.database.collection("orders"), current
        )
        cancelled = []
        for order in expired:
            order_service.cancel_expired_order(order)
            cancelled.append(order)
        return cancelled

    @staticmethod
    def remaining_seconds(order, now: datetime = None) -> int:
        """计算订单剩余支付秒数，供界面倒计时显示；已超时返回 0。"""
        current = now or datetime.now()
        delta = (order.expire_at - current).total_seconds()
        return max(0, int(delta))
