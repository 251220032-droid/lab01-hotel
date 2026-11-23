"""房型库存服务。

对应 UML 类图业务服务模块中的 ``InventoryService``，并依赖
``ConcurrencyLock`` 与 ``DailyInventory``。负责：

- 跨日连住的逐日库存校验（REQ-004）；
- 下单时加锁并扣减库存（REQ-005、REQ-008）；
- 取消或超时后释放库存（REQ-006）；
- 管理员对房型、每日库存、价格与停售状态的维护（REQ-002）。
"""

from datetime import timedelta

from ..models import RoomType, DailyInventory, RoomStatus
from ..core import ConcurrencyLock


class InventoryError(Exception):
    """库存相关业务异常。"""


class InventoryService:
    """管理库存校验、锁定、释放与后台维护。"""

    def __init__(self, database, lock: ConcurrencyLock = None) -> None:
        self._database = database
        self._lock = lock or ConcurrencyLock()

    @property
    def database(self):
        """关联数据库。"""
        return self._database

    @staticmethod
    def _date_range(check_in, check_out):
        """生成入住区间内的全部日期（不含离店当日）。"""
        if check_out <= check_in:
            raise InventoryError("离店日期必须晚于入住日期")
        days = (check_out - check_in).days
        return [check_in + timedelta(days=offset) for offset in range(days)]

    def get_room_type(self, room_type_id: int) -> RoomType:
        """获取房型，不存在则抛出异常。"""
        room_type = self._database.find_by_id("room_types", room_type_id)
        if room_type is None:
            raise InventoryError("房型不存在")
        return room_type

    def check_daily_availability(self, room_type_id: int, check_in,
                                 check_out, quantity: int = 1) -> bool:
        """对入住期间逐日校验在售状态与库存，全部满足返回 True。"""
        room_type = self.get_room_type(room_type_id)
        for target_date in self._date_range(check_in, check_out):
            if not room_type.is_available(target_date, quantity):
                return False
        return True

    def lock_inventory(self, room_type_id: int, check_in, check_out,
                       quantity: int = 1) -> bool:
        """对入住期间每个日期加锁并扣减库存。

        任一日期抢锁失败或库存不足，都会回滚此前已扣减的库存，
        保证不会出现部分锁定。成功返回 True。
        """
        room_type = self.get_room_type(room_type_id)
        dates = self._date_range(check_in, check_out)
        held_keys = []
        try:
            for target_date in dates:
                key = self._lock.build_key(room_type_id, target_date)
                if not self._lock.acquire(key):
                    return False
                held_keys.append(key)
                inventory = room_type.get_inventory(target_date)
                if inventory is None or inventory.status != RoomStatus.ON_SALE:
                    return False
                if not inventory.decrease(quantity):
                    return False
            return True
        finally:
            # 无论成功与否，立即释放本线程持有的锁（扣减结果保留）。
            for key in held_keys:
                self._lock.release(key)

    def release_inventory(self, room_type_id: int, check_in, check_out,
                          quantity: int = 1) -> None:
        """恢复入住期间的库存，用于取消订单与超时释放。"""
        room_type = self.get_room_type(room_type_id)
        for target_date in self._date_range(check_in, check_out):
            inventory = room_type.get_inventory(target_date)
            if inventory is not None:
                inventory.increase(quantity)

    # ---------- 管理员维护方法 ----------
    def create_room_type(self, hotel_id: int, name: str, bed_type: str,
                         max_guests: int, **kwargs) -> RoomType:
        """新增房型。"""
        room_type_id = self._database.next_id("room_types")
        room_type = RoomType(room_type_id, hotel_id, name, bed_type,
                             max_guests, **kwargs)
        self._database.add("room_types", room_type)
        self._database.save()
        return room_type

    def upsert_inventory(self, room_type_id: int, target_date,
                         available_count: int, price: float) -> DailyInventory:
        """新增或更新某房型某日的库存与价格，拒绝负数。"""
        if available_count < 0 or price < 0:
            raise InventoryError("库存与价格不能为负数")
        room_type = self.get_room_type(room_type_id)
        inventory = room_type.get_inventory(target_date)
        if inventory is None:
            inventory = DailyInventory(room_type_id, target_date,
                                       available_count, price)
            room_type.add_inventory(inventory)
            self._database.add("inventories", inventory)
        else:
            inventory.update_price(price)
            # 通过差值调整，保留原有的增减逻辑校验。
            diff = available_count - inventory.available_count
            if diff > 0:
                inventory.increase(diff)
            elif diff < 0:
                inventory.decrease(-diff)
        self._database.save()
        return inventory

    def set_sale_status(self, room_type_id: int, target_date,
                        stop: bool) -> None:
        """设置某房型某日的停售或在售状态。"""
        room_type = self.get_room_type(room_type_id)
        inventory = room_type.get_inventory(target_date)
        if inventory is None:
            raise InventoryError("该日期尚无房态记录")
        if stop:
            inventory.stop_sale()
        else:
            inventory.resume_sale()
        self._database.save()

    def list_room_types(self) -> list:
        """返回全部房型。"""
        return self._database.collection("room_types")
