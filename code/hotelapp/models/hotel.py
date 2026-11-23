"""酒店资源模块的数据模型。

对应 UML 类图中的 ``Hotel``、``RoomType``、``DailyInventory``
以及枚举 ``RoomStatus``。三者之间是聚合关系：一家酒店包含多种
房型，每种房型又由若干日期的每日房态记录组成。
"""

from datetime import date as date_cls

from .enums import RoomStatus


class Hotel:
    """酒店实体，聚合其下的全部房型。"""

    def __init__(self, hotel_id: int, name: str, city: str, address: str,
                 rating: float = 5.0) -> None:
        self._hotel_id = hotel_id
        self._name = name
        self._city = city
        self._address = address
        self._rating = rating
        self._room_types = []

    @property
    def hotel_id(self) -> int:
        """酒店唯一标识。"""
        return self._hotel_id

    @property
    def name(self) -> str:
        """酒店名称。"""
        return self._name

    @property
    def city(self) -> str:
        """所在城市。"""
        return self._city

    @property
    def address(self) -> str:
        """详细地址。"""
        return self._address

    @property
    def rating(self) -> float:
        """顾客评分。"""
        return self._rating

    @property
    def room_types(self) -> list:
        """该酒店的全部房型。"""
        return self._room_types

    def add_room_type(self, room_type: "RoomType") -> None:
        """添加房型，避免重复加入同一房型。"""
        if room_type not in self._room_types:
            self._room_types.append(room_type)

    def find_room_type(self, room_type_id: int) -> "RoomType":
        """按标识查找房型，未找到返回 None。"""
        for room_type in self._room_types:
            if room_type.room_type_id == room_type_id:
                return room_type
        return None

    def to_dict(self) -> dict:
        """序列化酒店基本信息（房型通过 RoomType 单独持久化）。"""
        return {
            "hotel_id": self._hotel_id,
            "name": self._name,
            "city": self._city,
            "address": self._address,
            "rating": self._rating,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Hotel":
        """根据字典重建酒店实例。"""
        return cls(
            data["hotel_id"], data["name"], data["city"],
            data["address"], data.get("rating", 5.0),
        )


class RoomType:
    """房型实体，描述床型、可住人数、设施与每日房态。"""

    def __init__(self, room_type_id: int, hotel_id: int, name: str,
                 bed_type: str, max_guests: int, area: float = 0.0,
                 facilities=None, description: str = "") -> None:
        self._room_type_id = room_type_id
        self._hotel_id = hotel_id
        self._name = name
        self._bed_type = bed_type
        self._max_guests = max_guests
        self._area = area
        self._facilities = list(facilities) if facilities else []
        self._description = description
        self._inventories = []

    @property
    def room_type_id(self) -> int:
        """房型唯一标识。"""
        return self._room_type_id

    @property
    def hotel_id(self) -> int:
        """所属酒店标识。"""
        return self._hotel_id

    @property
    def name(self) -> str:
        """房型名称。"""
        return self._name

    @property
    def bed_type(self) -> str:
        """床型描述。"""
        return self._bed_type

    @property
    def max_guests(self) -> int:
        """最多可住人数。"""
        return self._max_guests

    @property
    def area(self) -> float:
        """房间面积（平方米）。"""
        return self._area

    @property
    def facilities(self) -> list:
        """设施标签列表。"""
        return self._facilities

    @property
    def description(self) -> str:
        """房型介绍。"""
        return self._description

    @property
    def inventories(self) -> list:
        """该房型的每日房态记录。"""
        return self._inventories

    def get_inventory(self, target_date: date_cls) -> "DailyInventory":
        """获取指定日期的房态记录，不存在则返回 None。"""
        for inventory in self._inventories:
            if inventory.inventory_date == target_date:
                return inventory
        return None

    def add_inventory(self, inventory: "DailyInventory") -> None:
        """添加或替换某日的房态记录。"""
        existing = self.get_inventory(inventory.inventory_date)
        if existing:
            self._inventories.remove(existing)
        self._inventories.append(inventory)
        self._inventories.sort(key=lambda item: item.inventory_date)

    def is_available(self, target_date: date_cls, quantity: int = 1) -> bool:
        """判断指定日期是否在售且有足够库存。"""
        inventory = self.get_inventory(target_date)
        return bool(inventory and inventory.status == RoomStatus.ON_SALE
                    and inventory.available_count >= quantity)

    def to_dict(self) -> dict:
        """序列化房型信息（每日房态单独持久化）。"""
        return {
            "room_type_id": self._room_type_id,
            "hotel_id": self._hotel_id,
            "name": self._name,
            "bed_type": self._bed_type,
            "max_guests": self._max_guests,
            "area": self._area,
            "facilities": self._facilities,
            "description": self._description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RoomType":
        """根据字典重建房型实例。"""
        return cls(
            data["room_type_id"], data["hotel_id"], data["name"],
            data["bed_type"], data["max_guests"], data.get("area", 0.0),
            data.get("facilities", []), data.get("description", ""),
        )


class DailyInventory:
    """某房型在某一日期的库存、价格与在售状态。"""

    def __init__(self, room_type_id: int, inventory_date: date_cls,
                 available_count: int, price: float,
                 status: RoomStatus = RoomStatus.ON_SALE) -> None:
        if available_count < 0:
            raise ValueError("库存数量不能为负数")
        if price < 0:
            raise ValueError("价格不能为负数")
        self._room_type_id = room_type_id
        self._date = inventory_date
        self._available_count = available_count
        self._price = price
        self._status = status

    @property
    def room_type_id(self) -> int:
        """所属房型标识。"""
        return self._room_type_id

    @property
    def inventory_date(self) -> date_cls:
        """房态对应日期。"""
        return self._date

    @property
    def available_count(self) -> int:
        """当前可售房数。"""
        return self._available_count

    @property
    def price(self) -> float:
        """当日价格。"""
        return self._price

    @property
    def status(self) -> RoomStatus:
        """在售或停售状态。"""
        return self._status

    def increase(self, quantity: int) -> None:
        """增加可售库存（如释放、退房）。"""
        if quantity <= 0:
            raise ValueError("增加数量必须为正数")
        self._available_count += quantity

    def decrease(self, quantity: int) -> bool:
        """扣减库存，库存不足时返回 False 且不修改数据。"""
        if quantity <= 0:
            raise ValueError("扣减数量必须为正数")
        if self._available_count < quantity:
            return False
        self._available_count -= quantity
        return True

    def update_price(self, new_price: float) -> None:
        """更新当日价格，拒绝负数。"""
        if new_price < 0:
            raise ValueError("价格不能为负数")
        self._price = new_price

    def stop_sale(self) -> None:
        """将该日期设为停售。"""
        self._status = RoomStatus.STOPPED

    def resume_sale(self) -> None:
        """将该日期恢复为在售。"""
        self._status = RoomStatus.ON_SALE

    def to_dict(self) -> dict:
        """序列化房态记录。"""
        return {
            "room_type_id": self._room_type_id,
            "date": self._date.isoformat(),
            "available_count": self._available_count,
            "price": self._price,
            "status": self._status.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DailyInventory":
        """根据字典重建房态记录。"""
        return cls(
            data["room_type_id"],
            date_cls.fromisoformat(data["date"]),
            data["available_count"],
            data["price"],
            RoomStatus[data["status"]],
        )
