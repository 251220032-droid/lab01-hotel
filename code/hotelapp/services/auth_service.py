"""认证与权限服务。

对应 UML 类图业务服务模块中的 ``AuthService``，负责用户注册、
登录认证与权限校验（REQ-001）。用户实体的创建与口令哈希由
模型层完成，本服务聚焦业务规则：用户名唯一、口令匹配、
当前登录用户是否具备某项权限。
"""

from ..models import (
    Customer, Receptionist, Admin, UserRole,
)


class AuthError(Exception):
    """认证相关业务异常，便于界面捕获并提示。"""


class AuthService:
    """处理注册、登录与权限判断。"""

    def __init__(self, database) -> None:
        self._database = database
        self._current_user = None

    @property
    def database(self):
        """关联的数据库对象。"""
        return self._database

    @property
    def current_user(self):
        """当前登录用户，未登录为 None。"""
        return self._current_user

    def register(self, role: UserRole, username: str, password: str,
                 phone: str = ""):
        """注册新用户，用户名重复时抛出 AuthError。"""
        username = (username or "").strip()
        if not username:
            raise AuthError("用户名不能为空")
        if not password or len(password) < 6:
            raise AuthError("密码长度至少为 6 位")
        if self._database.find_user_by_name(username) is not None:
            raise AuthError("该用户名已被注册")

        user_id = self._database.next_id("users")
        user_cls = self._role_class(role)
        user = user_cls(user_id, username, password, phone)
        self._database.add_user(user)
        self._database.save()
        return user

    @staticmethod
    def _role_class(role: UserRole):
        """角色枚举到具体用户类的映射。"""
        mapping = {
            UserRole.CUSTOMER: Customer,
            UserRole.RECEPTIONIST: Receptionist,
            UserRole.ADMIN: Admin,
        }
        if role not in mapping:
            raise AuthError("未知的用户角色")
        return mapping[role]

    def login(self, username: str, password: str):
        """校验用户名与口令，成功后记录为当前用户并返回。"""
        user = self._database.find_user_by_name((username or "").strip())
        if user is None or not user.check_password(password):
            raise AuthError("用户名或密码错误")
        self._current_user = user
        return user

    def logout(self) -> None:
        """退出登录。"""
        self._current_user = None

    def require_login(self):
        """要求已登录，否则抛出 AuthError。"""
        if self._current_user is None:
            raise AuthError("请先登录")
        return self._current_user

    def check_permission(self, code: str) -> bool:
        """判断当前用户是否拥有指定权限。"""
        if self._current_user is None:
            return False
        return self._current_user.has_permission(code)

    def require_permission(self, code: str) -> None:
        """要求当前用户具备指定权限，否则抛出 AuthError。"""
        self.require_login()
        if not self.check_permission(code):
            raise AuthError("权限不足")
