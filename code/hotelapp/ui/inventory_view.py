"""后台房态库存管理视图。

对应界面 5（酒店资源模块）。以表格管理各房型在不同日期的
库存、价格与在售/停售状态，并提供新增与编辑表单。
"""

import tkinter as tk
from tkinter import ttk
from datetime import date

from ..models import RoomStatus
from .widgets import show_error, show_info


class InventoryView(ttk.Frame):
    """管理员房态管理界面。"""

    def __init__(self, parent, context) -> None:
        super().__init__(parent)
        self._context = context
        self._selected = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="房态库存管理",
                  style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="新增房态", style="Primary.TButton",
                   command=self._edit_form).pack(side="right")

        table_frame = ttk.Frame(self, padding=(12, 0))
        table_frame.pack(expand=True, fill="both")
        columns = ("room", "date", "count", "price", "status")
        self._tree = ttk.Treeview(table_frame, columns=columns,
                                  show="headings", selectmode="browse")
        headings = {"room": "房型", "date": "日期", "count": "库存数量",
                    "price": "每日价格", "status": "在售状态"}
        widths = {"room": 180, "date": 140, "count": 100, "price": 100,
                  "status": 100}
        for col in columns:
            self._tree.heading(col, text=headings[col])
            self._tree.column(col, width=widths[col], anchor="center")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.pack(expand=True, fill="both")

        editor = ttk.LabelFrame(self, text="编辑选中房态", padding=12)
        editor.pack(fill="x", padx=12, pady=12)
        self._count_var = tk.StringVar()
        self._price_var = tk.StringVar()
        ttk.Label(editor, text="库存").grid(row=0, column=0)
        ttk.Entry(editor, textvariable=self._count_var, width=10).grid(
            row=0, column=1, padx=8)
        ttk.Label(editor, text="价格").grid(row=0, column=2)
        ttk.Entry(editor, textvariable=self._price_var, width=10).grid(
            row=0, column=3, padx=8)
        ttk.Button(editor, text="保存修改",
                   command=self._save_selected).grid(row=0, column=4, padx=8)
        ttk.Button(editor, text="停售/恢复",
                   command=self._toggle_status).grid(row=0, column=5, padx=8)

    def refresh(self) -> None:
        """从数据库重新加载房态表格。"""
        for item in self._tree.get_children():
            self._tree.delete(item)
        for inventory in self._context.database.collection("inventories"):
            room_type = self._context.inventory.get_room_type(
                inventory.room_type_id)
            self._tree.insert(
                "", "end",
                values=(room_type.name, inventory.inventory_date.isoformat(),
                        inventory.available_count, f"¥{inventory.price}",
                        inventory.status.value))

    def _on_select(self, _event) -> None:
        """选中行后把数据载入编辑框。"""
        item = self._tree.focus()
        if not item:
            return
        values = self._tree.item(item, "values")
        self._selected = values
        self._count_var.set(values[2])
        self._price_var.set(values[4].replace("¥", ""))

    def _save_selected(self) -> None:
        """保存对选中房态的库存与价格修改。"""
        if not self._selected:
            show_error("未选择", "请先选择一条房态记录。")
            return
        try:
            room_name, date_text, _, _, _ = self._selected
            target_date = date.fromisoformat(date_text)
            room_type = self._find_room(room_name)
            self._context.inventory.upsert_inventory(
                room_type.room_type_id, target_date,
                int(self._count_var.get()), float(self._price_var.get()))
        except ValueError as exc:
            show_error("保存失败", f"输入不合法：{exc}")
            return
        show_info("已保存", "房态信息已更新。")
        self.refresh()

    def _toggle_status(self) -> None:
        """切换选中房态的停售/在售状态。"""
        if not self._selected:
            show_error("未选择", "请先选择一条房态记录。")
            return
        room_name, date_text, _, _, status_text = self._selected
        target_date = date.fromisoformat(date_text)
        room_type = self._find_room(room_name)
        stop = status_text != RoomStatus.STOPPED.value
        self._context.inventory.set_sale_status(
            room_type.room_type_id, target_date, stop)
        self.refresh()

    def _find_room(self, room_name: str):
        """按名称查找房型。"""
        for room_type in self._context.inventory.list_room_types():
            if room_type.name == room_name:
                return room_type
        return None

    def _edit_form(self) -> None:
        """新增房态的简化表单。"""
        dialog = tk.Toplevel(self)
        dialog.title("新增房态")
        dialog.transient(self)
        room_var = tk.StringVar(
            value=self._context.inventory.list_room_types()[0].name)
        date_var = tk.StringVar(value=date.today().isoformat())
        count_var = tk.StringVar(value="1")
        price_var = tk.StringVar(value="300")
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both")
        names = [r.name for r in self._context.inventory.list_room_types()]
        ttk.Label(frame, text="房型").grid(row=0, column=0, sticky="w")
        ttk.Combobox(frame, textvariable=room_var, values=names,
                     state="readonly").grid(row=0, column=1, padx=8, pady=4)
        ttk.Label(frame, text="日期").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=date_var).grid(row=1, column=1,
                                                     padx=8, pady=4)
        ttk.Label(frame, text="库存").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=count_var).grid(row=2, column=1,
                                                      padx=8, pady=4)
        ttk.Label(frame, text="价格").grid(row=3, column=0, sticky="w")
        ttk.Entry(frame, textvariable=price_var).grid(row=3, column=1,
                                                      padx=8, pady=4)

        def submit() -> None:
            try:
                room_type = self._find_room(room_var.get())
                self._context.inventory.upsert_inventory(
                    room_type.room_type_id, date.fromisoformat(date_var.get()),
                    int(count_var.get()), float(price_var.get()))
            except ValueError as exc:
                show_error("新增失败", str(exc))
                return
            dialog.destroy()
            self.refresh()

        ttk.Button(frame, text="确定", style="Primary.TButton",
                   command=submit).grid(row=4, column=0, columnspan=2,
                                       pady=(12, 0))
