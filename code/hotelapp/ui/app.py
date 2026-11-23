"""桌面应用主窗口。

负责登录视图与主工作台的切换、侧边导航、按角色显示菜单以及
关闭窗口时统一保存数据。它把各功能视图组织在一个容器中，
通过 ``show_view`` 在不同视图间切换。
"""

import tkinter as tk
from tkinter import ttk

from ..models import UserRole
from . import theme
from .login_view import LoginView
from .customer_home_view import CustomerHomeView
from .room_detail_view import RoomDetailView
from .my_orders_view import MyOrdersView
from .inventory_view import InventoryView
from .checkin_view import CheckInView
from .report_view import ReportView


class HotelApplication(tk.Tk):
    """应用主窗口。"""

    def __init__(self, context) -> None:
        super().__init__()
        self._context = context
        self.title("云栖酒店预订系统")
        self.geometry("1180x760")
        self.minsize(960, 640)
        self.configure(bg=theme.BG)
        self._style = ttk.Style(self)
        theme.configure_style(self._style)

        self._login = LoginView(self, context, self._after_login)
        self._login.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._workspace = ttk.Frame(self)
        self._views = {}
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- 登录 / 退出 ----------
    def _after_login(self) -> None:
        """登录成功后构建工作台并切换显示。"""
        self._build_workspace()
        self._login.place_forget()
        self._workspace.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _build_workspace(self) -> None:
        """根据角色构建侧边导航与视图容器。"""
        sidebar = ttk.Frame(self._workspace, style="Sidebar.TFrame", width=180)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        ttk.Label(sidebar, text="云栖酒店", style="Sidebar.TLabel",
                  font=(theme.FONT_FAMILY, 15, "bold")).pack(
                      anchor="w", padx=16, pady=20)

        container = ttk.Frame(self._workspace)
        container.pack(side="left", expand=True, fill="both")

        self._views = self._create_views(container)
        for key, view in self._views.items():
            view.place(relx=0, rely=0, relwidth=1, relheight=1)

        role = self._context.auth.current_user.role
        for key, label in self._menu_items(role):
            self._nav_button(sidebar, label,
                             command=lambda k=key: self.show_view(k))
        ttk.Button(sidebar, text="退出登录",
                   command=self._logout).pack(side="bottom", pady=16)

        first_key = self._default_view(role)
        self.show_view(first_key)

    def _nav_button(self, parent, label, command) -> None:
        """创建侧边导航按钮。"""
        tk.Button(parent, text=label, bg=theme.SIDEBAR, fg="#FFFFFF",
                  activebackground=theme.PRIMARY, activeforeground="#FFFFFF",
                  relief="flat", font=theme.FONT_BODY, padx=16, pady=10,
                  anchor="w", command=command).pack(fill="x")

    def _create_views(self, container) -> dict:
        """实例化全部可能用到的视图。"""
        return {
            "home": CustomerHomeView(
                container, self._context, self._open_detail),
            "detail": RoomDetailView(
                container, self._context,
                lambda: self.show_view("home"),
                lambda: self.show_view("orders")),
            "orders": MyOrdersView(container, self._context),
            "inventory": InventoryView(container, self._context),
            "checkin": CheckInView(container, self._context),
            "report": ReportView(container, self._context),
        }

    @staticmethod
    def _menu_items(role: UserRole) -> list:
        """按角色返回可访问的导航项。"""
        if role == UserRole.CUSTOMER:
            return [("home", "首页 / 搜索"), ("orders", "我的订单")]
        if role == UserRole.RECEPTIONIST:
            return [("checkin", "入住核销")]
        return [
            ("inventory", "房态库存"),
            ("checkin", "入住核销"),
            ("report", "经营报表"),
        ]

    @staticmethod
    def _default_view(role: UserRole) -> str:
        """返回角色登录后的默认视图。"""
        if role == UserRole.CUSTOMER:
            return "home"
        if role == UserRole.RECEPTIONIST:
            return "checkin"
        return "inventory"

    def _open_detail(self, room_type_id: int) -> None:
        """打开房型详情并切换到该视图。"""
        self._views["detail"].set_room_type(room_type_id)
        self.show_view("detail")

    def show_view(self, key: str) -> None:
        """切换到指定视图，并触发其刷新。"""
        view = self._views[key]
        view.tkraise()
        if hasattr(view, "refresh"):
            view.refresh()

    def _logout(self) -> None:
        """退出登录返回登录视图。"""
        self._context.auth.logout()
        self._workspace.place_forget()
        self._workspace.destroy()
        self._workspace = ttk.Frame(self)
        self._login.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _on_close(self) -> None:
        """关闭窗口前保存数据。"""
        self._context.shutdown()
        self.destroy()
