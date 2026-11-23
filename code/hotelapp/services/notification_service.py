"""短信通知服务。

对应 UML 类图系统支撑模块中的 ``NotificationService``，在支付
成功、订单取消、批量退款等事件发生时向用户发送短信提醒。
本模块做本地模拟：不真正访问短信网关，而是把发送内容记录
在内存列表中，便于界面展示与单元测试。
"""

from datetime import datetime


class NotificationService:
    """生成并记录短信通知。"""

    def __init__(self) -> None:
        self._messages = []

    @property
    def messages(self) -> list:
        """已发送的短信记录。"""
        return self._messages

    def send_sms(self, phone: str, message: str) -> dict:
        """发送一条短信并记录，返回发送内容。"""
        if not phone:
            raise ValueError("手机号不能为空")
        record = {
            "phone": phone,
            "message": message,
            "sent_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._messages.append(record)
        return record

    def notify_order_confirmed(self, order, phone: str) -> dict:
        """支付成功后发送预订确认通知。"""
        text = (
            f"您的订单 {order.order_id} 已确认，"
            f"入住日期 {order.check_in_date}，请按时到店。"
        )
        return self.send_sms(phone, text)

    def notify_order_cancelled(self, order, phone: str) -> dict:
        """订单取消后发送通知。"""
        text = f"您的订单 {order.order_id} 已取消，如有退款将原路返回。"
        return self.send_sms(phone, text)

    def clear(self) -> None:
        """清空发送记录。"""
        self._messages = []
