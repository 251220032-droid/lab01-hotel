"""可复用的界面组件。

封装卡片、统计卡片、徽章、带标签输入框与消息提示，避免在各
视图中重复编写布局代码。所有组件基于标准 ttk/tkinter 控件。
"""

import tkinter as tk
from tkinter import ttk, messagebox

from . import theme


class Card(ttk.Frame):
    """带边框与内边距的卡片容器。"""

    def __init__(self, parent, **kwargs) -> None:
        padding = kwargs.pop("padding", theme.PADDING)
        super().__init__(parent, style="Surface.TFrame", **kwargs)
        self._border = tk.Frame(self, bg=theme.BORDER)
        self._inner = ttk.Frame(self._border, style="Surface.TFrame")
        self._inner.pack(expand=True, fill="both", padx=1, pady=1)
        self._border.pack(expand=True, fill="both")
        self._inner.configure(padding=padding)

    @property
    def body(self) -> ttk.Frame:
        """卡片内部容器，子控件应添加到这里。"""
        return self._inner


class StatCard(ttk.Frame):
    """展示单个指标的统计卡片。"""

    def __init__(self, parent, label: str, value: str, **kwargs) -> None:
        super().__init__(parent, style="Surface.TFrame", **kwargs)
        border = tk.Frame(self, bg=theme.BORDER)
        inner = ttk.Frame(border, style="Surface.TFrame", padding=theme.PADDING)
        ttk.Label(inner, text=label, style="Muted.TLabel",
                  background=theme.SURFACE).pack(anchor="w")
        self._value_label = ttk.Label(inner, text=value,
                                      font=(theme.FONT_FAMILY, 20, "bold"),
                                      background=theme.SURFACE,
                                      foreground=theme.TEXT)
        self._value_label.pack(anchor="w", pady=(4, 0))
        inner.pack(fill="both", padx=1, pady=1)
        border.pack(expand=True, fill="both")

    def set_value(self, value: str) -> None:
        """更新统计数值。"""
        self._value_label.configure(text=value)


class Badge(tk.Label):
    """状态徽章，用浅色背景与彩色文字表示状态。"""

    def __init__(self, parent, text: str, kind: str = "success", **kwargs) -> None:
        colors = {
            "success": (theme.SUCCESS_BG, theme.SUCCESS),
            "danger": (theme.DANGER_BG, theme.DANGER),
            "warning": (theme.WARNING_BG, theme.WARNING),
            "info": (theme.PRIMARY_LIGHT, theme.PRIMARY_DARK),
        }
        bg, fg = colors.get(kind, colors["info"])
        super().__init__(parent, text=text, bg=bg, fg=fg,
                         font=(theme.FONT_FAMILY, 9, "bold"), padx=8, pady=2,
                         **kwargs)


class LabeledEntry(ttk.Frame):
    """带标签的输入框。"""

    def __init__(self, parent, label: str, show: str = None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        ttk.Label(self, text=label).pack(anchor="w")
        self._var = tk.StringVar()
        self._entry = ttk.Entry(self, textvariable=self._var, width=28)
        if show:
            self._entry.configure(show=show)
        self._entry.pack(fill="x", pady=(4, 0))

    @property
    def variable(self) -> tk.StringVar:
        """输入变量，便于读取与设置。"""
        return self._var

    def get(self) -> str:
        """读取输入值。"""
        return self._var.get().strip()

    def set(self, value: str) -> None:
        """设置输入值。"""
        self._var.set(value)


def show_info(title: str, message: str) -> None:
    """弹出信息提示框。"""
    messagebox.showinfo(title, message)


def show_error(title: str, message: str) -> None:
    """弹出错误提示框。"""
    messagebox.showerror(title, message)


def confirm(title: str, message: str) -> bool:
    """弹出确认框，返回用户是否确认。"""
    return messagebox.askyesno(title, message)
