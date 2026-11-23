"""经营报表视图。

对应界面 7（核销与报表模块）。以统计卡片展示订单数、入住率、
营业额、取消率，并用 tk.Canvas 手绘营业额趋势折线与房型占比
条形图。
"""

import tkinter as tk
from tkinter import ttk

from . import theme
from .widgets import StatCard


class ReportView(ttk.Frame):
    """管理员经营数据报表界面。"""

    def __init__(self, parent, context) -> None:
        super().__init__(parent)
        self._context = context
        self._build()
        self.refresh()

    def _build(self) -> None:
        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="经营数据报表",
                  style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="刷新", command=self.refresh).pack(side="right")

        cards = ttk.Frame(self, padding=(12, 0))
        cards.pack(fill="x")
        self._order_card = StatCard(cards, "订单总数", "0")
        self._occupancy_card = StatCard(cards, "平均入住率", "0")
        self._revenue_card = StatCard(cards, "营业额", "0")
        self._cancel_card = StatCard(cards, "取消率", "0")
        for card in (self._order_card, self._occupancy_card,
                     self._revenue_card, self._cancel_card):
            card.pack(side="left", expand=True, fill="x", padx=6)

        charts = ttk.Frame(self, padding=12)
        charts.pack(expand=True, fill="both")
        self._line_canvas = tk.Canvas(charts, bg=theme.SURFACE,
                                      highlightthickness=1,
                                      highlightbackground=theme.BORDER)
        self._line_canvas.pack(side="left", expand=True, fill="both", padx=6)
        self._bar_canvas = tk.Canvas(charts, bg=theme.SURFACE,
                                     highlightthickness=1,
                                     highlightbackground=theme.BORDER)
        self._bar_canvas.pack(side="left", expand=True, fill="both", padx=6)

    def refresh(self) -> None:
        """重新计算指标并重绘图表。"""
        summary = self._context.reports.summary()
        self._order_card.set_value(f"{summary['order_count']} 单")
        self._occupancy_card.set_value(f"{summary['occupancy_rate']}%")
        self._revenue_card.set_value(f"¥{summary['revenue']}")
        self._cancel_card.set_value(f"{summary['cancel_rate']}%")
        self._draw_line(self._context.reports.revenue_trend())
        self._draw_bars(self._context.reports.room_type_share())

    def _draw_line(self, values) -> None:
        """在画布上绘制营业额趋势折线。"""
        self._line_canvas.delete("all")
        self._line_canvas.create_text(90, 18, text="营业额趋势",
                                      fill=theme.TEXT, font=theme.FONT_BUTTON)
        if not values:
            return
        width = max(self._line_canvas.winfo_width(), 300)
        height = max(self._line_canvas.winfo_height(), 200)
        top, bottom = 40, height - 30
        max_value = max(values) or 1
        step = (width - 80) / max(len(values) - 1, 1)
        points = []
        for index, value in enumerate(values):
            x = 40 + step * index
            y = bottom - (value / max_value) * (bottom - top)
            points.append((x, y))
        for index in range(len(points) - 1):
            self._line_canvas.create_line(
                points[index][0], points[index][1],
                points[index + 1][0], points[index + 1][1],
                fill=theme.PRIMARY, width=2)
        for x, y in points:
            self._line_canvas.create_oval(x - 3, y - 3, x + 3, y + 3,
                                          fill=theme.PRIMARY,
                                          outline=theme.PRIMARY)

    def _draw_bars(self, shares) -> None:
        """在画布上绘制房型订单占比条形图。"""
        self._bar_canvas.delete("all")
        self._bar_canvas.create_text(90, 18, text="房型订单占比",
                                     fill=theme.TEXT,
                                     font=theme.FONT_BUTTON)
        if not shares:
            self._bar_canvas.create_text(150, 120, text="暂无订单数据",
                                         fill=theme.TEXT_MUTED)
            return
        bar_height = 26
        gap = 18
        x0, x1 = 110, max(self._bar_canvas.winfo_width(), 300) - 30
        for index, (room_type_id, percent) in enumerate(shares.items()):
            y = 50 + index * (bar_height + gap)
            room_type = self._context.inventory.get_room_type(room_type_id)
            self._bar_canvas.create_text(
                55, y + bar_height / 2, text=room_type.name,
                fill=theme.TEXT, font=theme.FONT_SMALL)
            bar_width = (x1 - x0) * percent / 100
            self._bar_canvas.create_rectangle(
                x0, y, x0 + bar_width, y + bar_height,
                fill=theme.PRIMARY, outline=theme.PRIMARY)
            self._bar_canvas.create_text(
                x0 + bar_width + 18, y + bar_height / 2,
                text=f"{percent}%", fill=theme.TEXT, font=theme.FONT_SMALL)
