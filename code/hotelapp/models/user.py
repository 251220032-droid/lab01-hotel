"""用户权限模块的数据模型。

对应 UML 类图中的抽象类 ``User`` 及其三个子类 ``Customer``、
``Receptionist``、``Admin``。为避免明文存储密码（REQ-014），
这里使用标准库 ``hashlib`` 提供的 PBKDF2-SHA256 加盐哈希，
思路与 bcrypt 一致：不直接保存口令，只保存随机盐与派生摘要。
"""

from abc import ABC, abstractmethod
import hashlib
import hmac
import os

from .enums import UserRole

# PBKDF2 迭代次数与摘要长度，按当前常规安全强度取值。
_ITERATIONS = 120_000
_SALT_BYTES = 16
_HASH_BYTES = 32


def hash_password(password: str) -> str:
    """对明文口令生成加盐哈希，返回 ``salt$digest`` 形式的十六进制字符串。"""
    if not isinstance(password, str) or not password:
        raise ValueError("密码不能为空")
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _ITERATIONS, dklen=_HASH_BYTES
    )
    return salt.hex() + "$" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    """校验输入口令是否与保存的加盐哈希一致。"""
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, AttributeError):
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _ITERATIONS, dklen=len(expected)
    )
    return hmac.compare_digest(candidate, expected)


class User(ABC):
    """系统用户抽象基类，承载三类用户的公共属性与行为。"""

    def __init__(self, user_id: int, username: str, password: str,
                 phone: str = "", role: UserRole = None) -> None:
        self._user_id = user_id
        self._username = username
        # 构造时传入的若为明文则自动哈希；若已含分隔符则视为已哈希直接保存。
        self._password_hash = password if "$" in password else hash_password(password)
        self._phone = phone
        self._role = role

    @property
    def user_id(self) -> int:
        """用户唯一标识。"""
        return self._user_id

    @property
    def username(self) -> str:
        """登录用户名。"""
        return self._username

    @property
    def phone(self) -> str:
        """绑定手机号。"""
        return self._phone

    @property
    def role(self) -> UserRole:
        """用户角色，由子类确定。"""
        return self._role

    def check_password(self, password: str) -> bool:
        """验证登录口令是否正确。"""
        return verify_password(password, self._password_hash)

    def change_password(self, old_password: str, new_password: str) -> bool:
        """修改密码，需先验证旧口令，成功后返回 True。"""
        if not self.check_password(old_password):
            return False
        self._password_hash = hash_password(new_password)
        return True

    @abstractmethod
    def permission_codes(self) -> list:
        """返回该角色拥有的权限码列表，由子类实现。"""

    def has_permission(self, code: str) -> bool:
        """判断用户是否拥有指定权限。"""
        return code in self.permission_codes()

    def to_dict(self) -> dict:
        """序列化为可持久化的字典。"""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "password_hash": self._password_hash,
            "phone": self._phone,
            "role": self._role.name if self._role else None,
            "type": self.__class__.__name__,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """根据字典重建对应角色的用户实例。"""
        subclass = _USER_CLASSES.get(data.get("type", "User"), Customer)
        return subclass(
            user_id=data["user_id"],
            username=data["username"],
            password=data["password_hash"],
            phone=data.get("phone", ""),
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self._user_id}, name={self._username!r})"


class Customer(User):
    """顾客角色：可检索房型、下单、支付与查看自己的订单。"""

    def __init__(self, user_id: int, username: str, password: str, phone: str = "") -> None:
        super().__init__(user_id, username, password, phone, UserRole.CUSTOMER)

    def permission_codes(self) -> list:
        return ["room:search", "order:create", "order:pay", "order:view"]


class Receptionist(User):
    """前台服务人员：可办理入住核销与退房。"""

    def __init__(self, user_id: int, username: str, password: str, phone: str = "") -> None:
        super().__init__(user_id, username, password, phone, UserRole.RECEPTIONIST)

    def permission_codes(self) -> list:
        return ["checkin:handle", "checkout:handle", "order:view"]


class Admin(User):
    """平台管理员：拥有资源维护、权限管理、批量退款与报表等全部后台权限。"""

    def __init__(self, user_id: int, username: str, password: str, phone: str = "") -> None:
        super().__init__(user_id, username, password, phone, UserRole.ADMIN)

    def permission_codes(self) -> list:
        return [
            "room:search", "order:view", "checkin:handle", "checkout:handle",
            "inventory:manage", "permission:manage", "order:batchcancel",
            "report:view", "log:view", "backup:manage",
        ]


# 角色名到具体类的映射，供反序列化使用。
_USER_CLASSES = {
    "Customer": Customer,
    "Receptionist": Receptionist,
    "Admin": Admin,
}
