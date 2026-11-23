"""应用上下文：组装全部服务并管理演示数据。

该模块是界面层、命令行入口与测试的统一入口，负责确定数据
文件位置、创建数据库与各业务服务，并在首次运行时写入一套
演示数据（酒店、房型、未来两周房态与三个角色的演示账号）。
"""

import os
from datetime import date, timedelta

from ..core import Database, ConcurrencyLock
from ..core.exception_log import ExceptionLogManager
from ..models import (
    Customer, Receptionist, Admin, Hotel, RoomType,
    DailyInventory, RoomStatus,
)
from .auth_service import AuthService
from .inventory_service import InventoryService
from .order_service import OrderService
from .payment_service import PaymentService
from .checkin_service import CheckInService
from .report_service import ReportService
from .backup_service import BackupService
from .notification_service import NotificationService


# 演示账号的统一初始口令（仅用于本地演示）。
DEMO_PASSWORD = "123456"


class ApplicationContext:
    """持有数据库与全部服务实例。"""

    def __init__(self, base_dir: str = None) -> None:
        base_dir = base_dir or os.path.join(os.getcwd(), "data")
        runtime_dir = os.path.join(base_dir, "runtime")
        backup_dir = os.path.join(base_dir, "backups")
        os.makedirs(runtime_dir, exist_ok=True)

        self.data_path = os.path.join(runtime_dir, "data.json")
        self.database = Database(self.data_path)
        self._restore_logs()

        self.lock = ConcurrencyLock()
        self.auth = AuthService(self.database)
        self.inventory = InventoryService(self.database, self.lock)
        self.orders = OrderService(self.database, self.inventory)
        self.payments = PaymentService(self.database, self.log_manager)
        self.checkin = CheckInService(self.database)
        self.reports = ReportService(self.database)
        self.backup = BackupService(
            self.data_path, backup_dir, self.log_manager,
        )
        self.notifications = NotificationService()

        if not self.database.users:
            self.seed_demo_data()

    def _restore_logs(self) -> None:
        """从数据库持久化内容恢复异常日志管理器。"""
        manager = ExceptionLogManager()
        manager.load_list([
            item.to_dict() for item in self.database.collection("exception_logs")
        ])
        self.log_manager = manager

    def seed_demo_data(self) -> None:
        """写入演示酒店、房型、房态与三个角色账号。"""
        # 三个角色的演示账号。
        customer = Customer(
            self.database.next_id("users"), "customer", DEMO_PASSWORD,
            "13800000001",
        )
        receptionist = Receptionist(
            self.database.next_id("users"), "reception", DEMO_PASSWORD,
            "13800000002",
        )
        admin = Admin(
            self.database.next_id("users"), "admin", DEMO_PASSWORD,
            "13800000003",
        )
        for user in (customer, receptionist, admin):
            self.database.add_user(user)

        hotel = Hotel(
            self.database.next_id("hotels"), "云栖酒店", "南京",
            "仙林大道 163 号", 4.8,
        )
        self.database.add("hotels", hotel)

        room_specs = [
            ("高级大床房", "1.8m 大床", 2, 328,
             ["免费WiFi", "含早餐", "独立空调"]),
            ("豪华双床房", "1.2m 双床", 2, 368,
             ["含双早", "免费WiFi"]),
            ("商务行政套房", "1.8m 大床", 2, 588,
             ["行政酒廊", "接送服务"]),
            ("经济单人房", "1.2m 单床", 1, 218,
             ["免费WiFi"]),
        ]
        today = date.today()
        for name, bed, guests, price, facilities in room_specs:
            room_type_id = self.database.next_id("room_types")
            room_type = RoomType(
                room_type_id, hotel.hotel_id, name, bed, guests,
                facilities=facilities,
            )
            self.database.add("room_types", room_type)
            for offset in range(14):
                target_date = today + timedelta(days=offset)
                count = 3 if name != "经济单人房" else 0 if offset == 0 else 2
                status = (RoomStatus.STOPPED if count == 0
                          else RoomStatus.ON_SALE)
                inventory = DailyInventory(
                    room_type_id, target_date, count,
                    price + (10 if offset >= 7 else 0), status,
                )
                room_type.add_inventory(inventory)
                self.database.add("inventories", inventory)
        self.database.save()

    def shutdown(self) -> None:
        """退出前统一保存数据。"""
        self.database.save()
