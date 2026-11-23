"""前台核销视图。

对应界面 6（核销与报表模块）。支持输入核销码办理入住/退房，
并以表格列出当前可核销的已确认订单。
"""

import tkinter as tk
from tkinter import ttk

from .widgets import show_error, show_info


class CheckInView(ttk.Frame):
    """前台入住核销与退房界面。"""

    def __init__(self, parent, context) -> None:
        super().__init__(parent)
        self._context = context
        self._build()
        self.refresh()

    def _build(self) -> None:
        ttk.Label(self, text="入住核销", style="Title.TLabel").pack(
            anchor="w", padx=12, pady=12)

        code_frame = ttk.LabelFrame(self, text="扫描或输入核销码", padding=12)
        code_frame.pack(fill="x", padx=12)
        self._code_var = tk.StringVar()
        ttk.Entry(code_frame, textvariable=self._code_var,
                  width=20).pack(side="left", padx=(0, 8))
        ttk.Button(code_frame, text="办理入住", style="Primary.TButton",
                   command=self._check_in).pack(side="left", padx=4)
        ttk.Button(code_frame, text="办理退房",
                   command=self._check_out).pack(side="left", padx=4)

        table_frame = ttk.Frame(self, padding=12)
        table_frame.pack(expand=True, fill="both")
        columns = ("order", "room", "date", "code", "status")
        self._tree = ttk.Treeview(table_frame, columns=columns,
                                  show="headings")
        headings = {"order": "订单号", "room": "房型", "date": "入住/离店",
                    "code": "核销码", "status": "状态"}
        for col in columns:
            self._tree.heading(col, text=headings[col])
            self._tree.column(col, anchor="center", width=130)
        self._tree.pack(expand=True, fill="both")
        self._tree.bind("<<TreeviewSelect>>", self._fill_code)

    def _fill_code(self, _event) -> None:
        """选中表格行后自动填入核销码。"""
        item = self._tree.focus()
        if item:
            values = self._tree.item(item, "values")
            self._code_var.set(values[3])

    def refresh(self) -> None:
        """重新加载可核销订单。"""
        for item in self._tree.get_children():
            self._tree.delete(item)
        for order in self._context.checkin.pending_checkin_orders():
            room_type = self._context.inventory.get_room_type(
                order.room_type_id)
            period = f"{order.check_in_date}/{order.check_out_date}"
            self._tree.insert(
                "", "end",
                values=(order.order_id, room_type.name, period,
                        order.check_code, order.status.value))

    def _find_order(self, code: str):
        """按核销码查找订单。"""
        return self._context.checkin.find_order_by_code(code)

    def _check_in(self) -> None:
        """办理入住。"""
        code = self._code_var.get().strip()
        order = self._find_order(code)
        try:
            self._context.checkin.handle_check_in(order, code)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            show_error("核销失败", str(exc))
            return
        show_info("核销成功", f"订单 {order.order_id} 已办理入住。")
        self.refresh()

    def _check_out(self) -> None:
        """办理退房。"""
        code = self._code_var.get().strip()
        order = self._find_order(code)
        if order is None:
            show_error("退房失败", "核销码不正确。")
            return
        try:
            self._context.checkin.handle_check_out(order)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            show_error("退房失败", str(exc))
            return
        show_info("退房成功", f"订单 {order.order_id} 已完成。")
        self.refresh()
