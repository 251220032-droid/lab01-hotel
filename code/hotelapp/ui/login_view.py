"""登录 / 注册视图。

对应界面 1（用户权限模块）。提供登录与注册两种模式，注册时
可选择角色。认证成功后通过回调通知主应用切换到对应工作台。
"""

import tkinter as tk
from tkinter import ttk

from ..models import UserRole
from . import theme
from .widgets import LabeledEntry, show_error


class LoginView(ttk.Frame):
    """登录与注册界面。"""

    def __init__(self, parent, context, on_login) -> None:
        super().__init__(parent)
        self._context = context
        self._on_login = on_login
        self._is_register = tk.BooleanVar(value=False)
        self._role_var = tk.StringVar(value=UserRole.CUSTOMER.name)
        self._build()

    def _build(self) -> None:
        # 居中卡片。
        wrapper = ttk.Frame(self, style="Surface.TFrame")
        wrapper.place(relx=0.5, rely=0.5, anchor="center")
        card = tk.Frame(wrapper, bg=theme.BORDER)
        inner = ttk.Frame(card, style="Surface.TFrame", padding=32)
        inner.pack(padx=1, pady=1)
        card.pack()

        self._title = ttk.Label(inner, text="账号登录",
                                style="Heading.TLabel")
        self._title.pack(anchor="w")
        ttk.Label(inner, text="云栖酒店预订系统",
                  background=theme.SURFACE, foreground=theme.TEXT_MUTED).pack(
                      anchor="w", pady=(0, 12))

        self._username = LabeledEntry(inner, "用户名")
        self._username.pack(fill="x")
        self._password = LabeledEntry(inner, "密码", show="*")
        self._password.pack(fill="x", pady=(10, 0))

        self._role_frame = ttk.Frame(inner, style="Surface.TFrame")
        ttk.Label(self._role_frame, text="注册角色",
                  background=theme.SURFACE).pack(anchor="w")
        ttk.Combobox(self._role_frame, textvariable=self._role_var,
                     values=[r.name for r in UserRole],
                     state="readonly").pack(fill="x", pady=(4, 0))

        ttk.Checkbutton(inner, text="没有账号？切换到注册",
                        variable=self._is_register,
                        command=self._toggle_mode).pack(anchor="w",
                                                        pady=(12, 0))
        self._submit = ttk.Button(inner, text="登录", style="Primary.TButton",
                                  command=self._submit_form)
        self._submit.pack(fill="x", pady=(16, 0))

    def _toggle_mode(self) -> None:
        register = self._is_register.get()
        self._title.configure(text="注册账号" if register else "账号登录")
        self._submit.configure(text="注册" if register else "登录")
        if register:
            self._role_frame.pack(fill="x", pady=(10, 0))
        else:
            self._role_frame.pack_forget()

    def _submit_form(self) -> None:
        username = self._username.get()
        password = self._password.get()
        try:
            if self._is_register.get():
                role = UserRole[self._role_var.get()]
                self._context.auth.register(role, username, password)
                self._context.auth.login(username, password)
            else:
                self._context.auth.login(username, password)
        # 认证与注册异常统一提示。
        except Exception as exc:  # pylint: disable=broad-exception-caught
            show_error("操作失败", str(exc))
            return
        self._on_login()
