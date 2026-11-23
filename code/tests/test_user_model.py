"""用户实体、口令哈希与权限的单元测试。"""

import pytest

from hotelapp.models import (
    Customer, Receptionist, Admin, UserRole,
)
from hotelapp.models.user import hash_password, verify_password


def test_hash_and_verify_password():
    """正确口令校验通过，错误口令失败，且哈希不含明文。"""
    stored = hash_password("secret123")
    assert "secret123" not in stored
    assert verify_password("secret123", stored)
    assert not verify_password("wrong", stored)


def test_each_hash_uses_distinct_salt():
    """同一口令两次哈希结果应不同（随机盐）。"""
    assert hash_password("abcdef") != hash_password("abcdef")


def test_verify_handles_corrupt_storage():
    """损坏的哈希字符串应安全返回 False 而非抛异常。"""
    assert not verify_password("x", "no-separator")
    assert not verify_password("x", "")


def test_empty_password_rejected():
    """空口令不允许生成哈希。"""
    with pytest.raises(ValueError):
        hash_password("")


def test_customer_password_auto_hashed():
    """构造用户时明文口令应被自动哈希，且能正确校验。"""
    user = Customer(1, "tester", "mypassword", "13800000000")
    assert user.check_password("mypassword")
    assert not user.check_password("other")


def test_change_password():
    """修改密码需校验旧口令，成功后新口令生效。"""
    user = Customer(1, "tester", "oldpass", "")
    assert not user.change_password("bad", "newpass")
    assert user.change_password("oldpass", "newpass")
    assert user.check_password("newpass")


def test_role_and_permissions():
    """三个角色的角色枚举与权限码应符合预期。"""
    customer = Customer(1, "c", "123456")
    receptionist = Receptionist(2, "r", "123456")
    admin = Admin(3, "a", "123456")
    assert customer.role == UserRole.CUSTOMER
    assert customer.has_permission("order:create")
    assert not customer.has_permission("report:view")
    assert receptionist.has_permission("checkin:handle")
    assert not receptionist.has_permission("inventory:manage")
    assert admin.has_permission("report:view")
    assert admin.has_permission("inventory:manage")
