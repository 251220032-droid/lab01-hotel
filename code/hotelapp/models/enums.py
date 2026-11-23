"""系统中使用的全部枚举类型。

这些枚举对应 UML 类图中的三个枚举类，并补充了角色枚举，
用于在数据模型与业务服务之间表达有限、确定的取值集合。
"""

from enum import Enum


class UserRole(Enum):
    """三类系统参与者的角色。"""

    CUSTOMER = "顾客"
    RECEPTIONIST = "前台服务人员"
    ADMIN = "平台管理员"


class RoomStatus(Enum):
    """每日房态：在售或停售。"""

    ON_SALE = "在售"
    STOPPED = "停售"


class OrderStatus(Enum):
    """订单生命周期状态。"""

    PENDING_PAYMENT = "待支付"
    CONFIRMED = "已确认"
    CANCELLED = "已取消"
    COMPLETED = "已完成"


class PaymentMethod(Enum):
    """支持的支付方式。"""

    ALIPAY = "支付宝"
    WECHAT = "微信支付"
    BANK_CARD = "银行卡"


class CheckStatus(Enum):
    """核销操作的结果状态，主要用于界面与日志展示。"""

    CHECKED_IN = "已入住"
    CHECKED_OUT = "已退房"
