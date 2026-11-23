"""顾客首页视图。

对应界面 2（搜索查询模块）。提供城市、日期、房型条件与可滚动
的房型卡片列表，点击"立即预订"进入房型详情。
"""

import tkinter as tk
from tkinter import ttk
from datetime import date, timedelta

from . import theme
from .widgets import show_error


class ScrollableFrame(ttk.Frame):
    """带垂直滚动条的容器。"""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self._canvas = tk.Canvas(self, bg=theme.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical",
                                  command=self._canvas.yview)
        self.body = ttk.Frame(self._canvas)
        self.body.bind(
            "<Configure>",
            lambda _event: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")),
        )
        self._window = self._canvas.create_window(
            (0, 0), window=self.body, anchor="nw")
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.bind("<Configure>", self._on_resize)
        self._canvas.pack(side="left", expand=True, fill="both")
        scrollbar.pack(side="right", fill="y")

    def _on_resize(self, event) -> None:
        """让内部框架宽度跟随画布，避免横向留白。"""
        self._canvas.itemconfigure(self._window, width=event.width)


class CustomerHomeView(ttk.Frame):
    """顾客搜索与房型列表界面。"""

    def __init__(self, parent, context, on_select_room) -> None:
        super().__init__(parent)
        self._context = context
        self._on_select_room = on_select_room
        self._build_search()
        self._list = ScrollableFrame(self)
        self._list.pack(expand=True, fill="both", padx=12, pady=(0, 12))
        self.refresh()

    def _build_search(self) -> None:
        search_bar = ttk.Frame(self, padding=12)
        search_bar.pack(fill="x")
        today = date.today()
        self._city = tk.StringVar(value="南京")
        self._check_in = tk.StringVar(
            value=today.isoformat())
        self._check_out = tk.StringVar(
            value=(today + timedelta(days=1)).isoformat())
        self._room_name = tk.StringVar(value="全部")

        for column, (label, var) in enumerate([
            ("城市", self._city),
            ("入住日期", self._check_in),
            ("离店日期", self._check_out),
        ]):
            ttk.Label(search_bar, text=label).grid(
                row=0, column=column * 2, padx=4)
            ttk.Entry(search_bar, textvariable=var, width=14).grid(
                row=0, column=column * 2 + 1, padx=4)
        names = ["全部"] + [r.name for r in self._context.inventory.list_room_types()]
        ttk.Label(search_bar, text="房型").grid(row=0, column=6, padx=4)
        ttk.Combobox(search_bar, textvariable=self._room_name, values=names,
                     state="readonly", width=12).grid(row=0, column=7, padx=4)
        ttk.Button(search_bar, text="搜索", style="Primary.TButton",
                   command=self.refresh).grid(row=0, column=8, padx=8)

    def refresh(self) -> None:
        """按搜索条件刷新房型卡片。"""
        for child in self._list.body.winfo_children():
            child.destroy()
        try:
            check_in = date.fromisoformat(self._check_in.get())
            check_out = date.fromisoformat(self._check_out.get())
        except ValueError:
            show_error("日期格式错误", "请使用 YYYY-MM-DD 格式")
            return
        room_types = self._context.inventory.list_room_types()
        matched = 0
        for room_type in room_types:
            if self._room_name.get() != "全部" and \
                    room_type.name != self._room_name.get():
                continue
            available = self._context.inventory.check_daily_availability(
                room_type.room_type_id, check_in, check_out)
            self._render_card(room_type, check_in, check_out, available)
            matched += 1
        if matched == 0:
            ttk.Label(self._list.body, text="未找到匹配房型",
                      style="Muted.TLabel").pack(pady=30)

    def _render_card(self, room_type, check_in, check_out, available) -> None:
        border = tk.Frame(self._list.body, bg=theme.BORDER)
        inner = ttk.Frame(border, style="Surface.TFrame", padding=12)
        ttk.Label(inner, text=room_type.name,
                  style="Heading.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(inner, text=f"床型 {room_type.bed_type}，"
                              f"可住 {room_type.max_guests} 人",
                  background=theme.SURFACE,
                  foreground=theme.TEXT_MUTED).grid(row=1, column=0,
                                                    sticky="w", pady=4)
        amount = self._context.orders.calculate_amount(
            room_type.room_type_id, check_in, check_out)
        ttk.Label(inner, text=f"参考价 ¥{amount}",
                  background=theme.SURFACE,
                  foreground=theme.ACCENT,
                  font=theme.FONT_BUTTON).grid(row=2, column=0, sticky="w")
        state_text = "可预订" if available else "所选日期无房"
        ttk.Button(inner, text=state_text, style="Primary.TButton",
                   state="normal" if available else "disabled",
                   command=lambda rt=room_type:
                   self._on_select_room(rt.room_type_id)).grid(
                       row=0, column=1, rowspan=3, padx=12)
        inner.columnconfigure(0, weight=1)
        inner.pack(fill="x", padx=1, pady=1)
        border.pack(fill="x", pady=6)
