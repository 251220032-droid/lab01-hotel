"""数据持久化组件。

本模块是系统的单一数据访问对象，负责把用户、酒店、房型、房态、
订单、支付、异常日志等实体持久化到 JSON 文件，并在内存中维护
对象集合。写入采用"先写临时文件再原子替换"的方式，避免程序
中途退出导致数据文件损坏。

选择 JSON 而非内置 sqlite，是为了让数据结构与 UML 模型直接
对应、便于人工检查；后续若需更强的查询能力，可在不改动服务层
接口的前提下替换为数据库实现。
"""

import json
import os

from ..models import (
    Customer, Receptionist, Admin,
    Hotel, RoomType, DailyInventory,
    Order, Payment,
)
from .exception_log import ExceptionLog

# 集合名 -> (实体类, 反序列化方法)。
_COLLECTION_TYPES = {
    "hotels": Hotel,
    "room_types": RoomType,
    "inventories": DailyInventory,
    "orders": Order,
    "payments": Payment,
    "exception_logs": ExceptionLog,
}
_USER_TYPES = {"Customer": Customer, "Receptionist": Receptionist, "Admin": Admin}


class Database:
    """基于 JSON 文件的仓储，统一管理实体集合与主键序列。"""

    def __init__(self, data_path: str) -> None:
        self._data_path = data_path
        self._users = []
        self._collections = {name: [] for name in _COLLECTION_TYPES}
        self._sequences = {}
        self.load()

    # ---------- 序列化与加载 ----------
    def load(self) -> None:
        """从磁盘加载数据；文件不存在时初始化为空库。"""
        if not os.path.exists(self._data_path):
            return
        with open(self._data_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self._users = [self._load_user(item) for item in payload.get("users", [])]
        for name, cls in _COLLECTION_TYPES.items():
            self._collections[name] = [
                cls.from_dict(item) for item in payload.get(name, [])
            ]
        self._sequences = payload.get("sequences", {})
        self._relate_inventories()

    def _relate_inventories(self) -> None:
        """把每日房态重新挂回所属房型，重建内存聚合关系。

        持久化时房型与房态是分开存储的，加载后需要恢复
        ``RoomType -> DailyInventory`` 的聚合，否则按日期查询
        房态会返回 None。
        """
        room_types = {
            room_type.room_type_id: room_type
            for room_type in self._collections["room_types"]
        }
        for inventory in self._collections["inventories"]:
            room_type = room_types.get(inventory.room_type_id)
            if room_type is not None:
                room_type.add_inventory(inventory)

    @staticmethod
    def _load_user(item: dict):
        """根据保存的类型字段重建具体角色用户。"""
        user_cls = _USER_TYPES.get(item.get("type"), Customer)
        return user_cls.from_dict(item)

    def save(self) -> None:
        """把当前内存数据原子写入磁盘。"""
        payload = {
            "users": [user.to_dict() for user in self._users],
            "sequences": self._sequences,
        }
        for name, items in self._collections.items():
            payload[name] = [item.to_dict() for item in items]
        directory = os.path.dirname(self._data_path) or "."
        os.makedirs(directory, exist_ok=True)
        tmp_path = self._data_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self._data_path)

    # ---------- 主键生成 ----------
    def next_id(self, sequence: str) -> int:
        """生成并返回指定集合的下一个自增主键。"""
        current = self._sequences.get(sequence, 0) + 1
        self._sequences[sequence] = current
        return current

    # ---------- 用户 ----------
    @property
    def users(self) -> list:
        """全部用户。"""
        return self._users

    def add_user(self, user) -> None:
        """添加用户。"""
        self._users.append(user)

    def find_user_by_name(self, username: str):
        """按用户名查找用户，未找到返回 None。"""
        for user in self._users:
            if user.username == username:
                return user
        return None

    def find_user_by_id(self, user_id: int):
        """按标识查找用户。"""
        for user in self._users:
            if user.user_id == user_id:
                return user
        return None

    # ---------- 通用集合访问 ----------
    def collection(self, name: str) -> list:
        """返回指定实体集合。"""
        return self._collections[name]

    def add(self, collection: str, entity) -> None:
        """向指定集合添加实体。"""
        self._collections[collection].append(entity)

    def find_by_id(self, collection: str, entity_id: int):
        """在指定集合中按主键查找实体。"""
        for entity in self._collections[collection]:
            accessor = getattr(entity, collection[:-1] + "_id", None)
            if accessor == entity_id:
                return entity
        return self._fallback_find(collection, entity_id)

    def _fallback_find(self, collection: str, entity_id: int):
        """针对命名不规则的集合（如 inventories）做标识匹配兜底。"""
        id_attrs = {
            "hotels": "hotel_id",
            "room_types": "room_type_id",
            "inventories": "room_type_id",
            "orders": "order_id",
            "payments": "payment_id",
            "exception_logs": "log_id",
        }
        attr = id_attrs.get(collection)
        if not attr:
            return None
        for entity in self._collections[collection]:
            if getattr(entity, attr, None) == entity_id:
                return entity
        return None
