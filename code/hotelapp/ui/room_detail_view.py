"""房型详情与预订下单视图。

对应界面 3（订单支付模块）。展示房型介绍、设施、日期与数量
选择、价格明细，点击"立即预订"创建待支付订单。
"""

import tkinter as tk
from tkinter import ttk
from datetime import date, timedelta

from . import theme
from .widgets import show_error, show_info


class RoomDetailView(ttk.Frame):
    """房型详情与下单界面。"""

    def __init__(self, parent, context, on_back, on_view_orders) -> None:
        super().__init__(parent)
        self._context = context
        self._on_back = on_back
        self._on_view_orders = on_view_orders
        self._room_type_id = None
        self._check_in = None
        self._check_out = None
        self._quantity = None
        self._amount_label = None
        self._build()

    def _build(self) -> None:
        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")
        ttk.Button(top, text="返回列表", command=self._on_back).pack(side="left")
        self._name_label = ttk.Label(top, text="", style="Title.TLabel")
        self._name_label.pack(side="left", padx=12)

        self._content = ttk.Frame(self, padding=12)
        self._content.pack(expand=True, fill="both")

    def set_room_type(self, room_type_id: int) -> None:
        """切换展示的房型并重建内容。"""
        self._room_type_id = room_type_id
        for child in self._content.winfo_children():
            child.destroy()
        room_type = self._context.inventory.get_room_type(room_type_id)
        self._name_label.configure(text=room_type.name)
        self._render_detail(room_type)

    def _render_detail(self, room_type) -> None:
        today = date.today()
        self._check_in = tk.StringVar(value=today.isoformat())
        self._check_out = tk.StringVar(
            value=(today + timedelta(days=1)).isoformat())
        self._quantity = tk.IntVar(value=1)

        info = ttk.LabelFrame(self._content, text="房型信息", padding=12)
        info.pack(fill="x")
        ttk.Label(info, text=f"床型：{room_type.bed_type}").pack(anchor="w")
        ttk.Label(info, text=f"可住：{room_type.max_guests} 人").pack(
            anchor="w", pady=4)
        ttk.Label(info, text="设施：" + "、".join(room_type.facilities)).pack(
            anchor="w")

        form = ttk.LabelFrame(self._content, text="预订信息", padding=12)
        form.pack(fill="x", pady=12)
        ttk.Label(form, text="入住日期").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self._check_in, width=16).grid(
            row=0, column=1, padx=8)
        ttk.Label(form, text="离店日期").grid(row=0, column=2, sticky="w")
        ttk.Entry(form, textvariable=self._check_out, width=16).grid(
            row=0, column=3, padx=8)
        ttk.Label(form, text="房间数量").grid(row=1, column=0, sticky="w",
                                              pady=(8, 0))
        ttk.Spinbox(form, from_=1, to=5, textvariable=self._quantity,
                    width=8).grid(row=1, column=1, sticky="w", padx=8,
                                  pady=(8, 0))

        ttk.Button(self._content, text="立即预订", style="Primary.TButton",
                   command=self._book).pack(fill="x")
        self._amount_label = ttk.Label(self._content, text="",
                                       foreground=theme.ACCENT,
                                       font=theme.FONT_BUTTON)
        self._amount_label.pack(pady=8)
        self._update_amount()

    def _update_amount(self) -> None:
        """实时计算并展示预计金额。"""
        try:
            check_in = date.fromisoformat(self._check_in.get())
            check_out = date.fromisoformat(self._check_out.get())
            amount = self._context.orders.calculate_amount(
                self._room_type_id, check_in, check_out, self._quantity.get())
            self._amount_label.configure(text=f"预计金额 ¥{amount}")
        except Exception:  # pylint: disable=broad-exception-caught
            # 日期非法或金额无法计算时不更新金额。
            self._amount_label.configure(text="")

    def _book(self) -> None:
        """提交预订，成功后提示并可前往订单页支付。"""
        try:
            check_in = date.fromisoformat(self._check_in.get())
            check_out = date.fromisoformat(self._check_out.get())
            user = self._context.auth.require_login()
            order = self._context.orders.create_order(
                user, self._room_type_id, check_in, check_out,
                self._quantity.get())
        except Exception as exc:  # pylint: disable=broad-exception-caught
            show_error("预订失败", str(exc))
            return
        if show_info("预订成功",
                     f"订单 {order.order_id} 已生成，请在 15 分钟内支付。"):
            self._on_view_orders()
