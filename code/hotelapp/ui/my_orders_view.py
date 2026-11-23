"""我的订单与支付视图。

对应界面 4（订单支付模块）。展示当前顾客的订单，待支付订单
提供 15 分钟倒计时、支付与取消；进入页面时先执行一次超时
扫描，自动取消已超时订单。
"""

import tkinter as tk
from tkinter import ttk

from ..models import OrderStatus, PaymentMethod
from ..core import TimeoutScheduler
from . import theme
from .widgets import show_error, show_info
from .customer_home_view import ScrollableFrame


class MyOrdersView(ttk.Frame):
    """顾客订单列表与支付界面。"""

    def __init__(self, parent, context) -> None:
        super().__init__(parent)
        self._context = context
        self._filter = tk.StringVar(value="全部")
        self._method = tk.StringVar(value=PaymentMethod.ALIPAY.name)
        self._build()
        self._list = ScrollableFrame(self)
        self._list.pack(expand=True, fill="both", padx=12, pady=(0, 12))

    def _build(self) -> None:
        toolbar = ttk.Frame(self, padding=12)
        toolbar.pack(fill="x")
        filters = ["全部", "待支付", "已确认", "已取消", "已完成"]
        for name in filters:
            ttk.Radiobutton(toolbar, text=name, value=name,
                            variable=self._filter,
                            command=self.refresh).pack(side="left", padx=4)
        ttk.Label(toolbar, text="支付方式").pack(side="left", padx=(20, 4))
        ttk.Combobox(toolbar, textvariable=self._method,
                     values=[m.name for m in PaymentMethod],
                     state="readonly", width=10).pack(side="left")
        ttk.Button(toolbar, text="刷新", command=self.refresh).pack(side="right")

    def refresh(self) -> None:
        """处理超时订单并按筛选条件重新渲染。"""
        TimeoutScheduler.auto_cancel(self._context.orders)
        for child in self._list.body.winfo_children():
            child.destroy()
        user = self._context.auth.require_login()
        orders = self._context.orders.orders_of_customer(user.user_id)
        for order in orders:
            if self._filter.get() != "全部" and \
                    order.status.value != self._filter.get():
                continue
            self._render_order(order)
        if not self._list.body.winfo_children():
            ttk.Label(self._list.body, text="暂无订单",
                      style="Muted.TLabel").pack(pady=30)

    def _render_order(self, order) -> None:
        border = tk.Frame(self._list.body, bg=theme.BORDER)
        inner = ttk.Frame(border, style="Surface.TFrame", padding=12)
        room_type = self._context.inventory.get_room_type(order.room_type_id)
        ttk.Label(inner, text=f"{room_type.name}  订单 {order.order_id}",
                  style="Heading.TLabel").pack(anchor="w")
        ttk.Label(inner,
                  text=f"入住 {order.check_in_date}，离店 "
                       f"{order.check_out_date}，共 {order.nights} 晚",
                  background=theme.SURFACE,
                  foreground=theme.TEXT_MUTED).pack(anchor="w", pady=4)
        ttk.Label(inner, text=f"金额 ¥{order.total_amount}，"
                              f"状态 {order.status.value}",
                  background=theme.SURFACE).pack(anchor="w")

        if order.status == OrderStatus.PENDING_PAYMENT:
            remain = TimeoutScheduler.remaining_seconds(order)
            ttk.Label(inner, text=f"剩余支付时间 {remain} 秒",
                      background=theme.SURFACE,
                      foreground=theme.DANGER).pack(anchor="w", pady=4)
            buttons = ttk.Frame(inner, style="Surface.TFrame")
            buttons.pack(fill="x")
            ttk.Button(buttons, text="立即支付", style="Primary.TButton",
                       command=lambda o=order: self._pay(o)).pack(side="right",
                                                                  padx=4)
            ttk.Button(buttons, text="取消订单",
                       command=lambda o=order: self._cancel(o)).pack(
                           side="right", padx=4)
        inner.pack(fill="x", padx=1, pady=1)
        border.pack(fill="x", pady=6)

    def _pay(self, order) -> None:
        """选择支付方式并发起支付。"""
        try:
            method = PaymentMethod[self._method.get()]
            self._context.payments.process_payment(order, method)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            show_error("支付失败", str(exc))
            return
        show_info("支付成功", f"订单 {order.order_id} 已确认。")
        self.refresh()

    def _cancel(self, order) -> None:
        """取消待支付订单。"""
        try:
            self._context.orders.cancel_order(order)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            show_error("取消失败", str(exc))
            return
        show_info("已取消", "订单已取消，库存已释放。")
        self.refresh()
