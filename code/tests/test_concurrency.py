"""并发锁非阻塞抢占语义的单元测试。"""

from datetime import date

import pytest

from hotelapp.core import ConcurrencyLock


def test_build_key_unique_by_room_and_date():
    """不同房型或日期生成不同资源键。"""
    day = date(2026, 11, 23)
    key1 = ConcurrencyLock.build_key(1, day)
    key2 = ConcurrencyLock.build_key(2, day)
    key3 = ConcurrencyLock.build_key(1, date(2026, 11, 24))
    assert key1 != key2
    assert key1 != key3


def test_nonblocking_acquire_fails_when_held():
    """锁被占用时，第二次非阻塞获取应立即失败。"""
    lock = ConcurrencyLock()
    key = "room:1:date:2026-11-23"
    assert lock.acquire(key)
    assert not lock.acquire(key)
    lock.release(key)
    assert lock.acquire(key)
    lock.release(key)


def test_try_lock_context_manager():
    """try_lock 进入抢锁、退出自动释放。"""
    lock = ConcurrencyLock()
    key = "room:1:date:2026-11-24"
    with lock.try_lock(key) as held:
        assert held
        assert not lock.acquire(key)
    assert lock.acquire(key)
    lock.release(key)


def test_release_unknown_key_raises():
    """释放从未创建的锁应抛出 KeyError。"""
    lock = ConcurrencyLock()
    with pytest.raises(KeyError):
        lock.release("missing")


def test_active_lock_count():
    """活动锁数量随获取的资源增长。"""
    lock = ConcurrencyLock()
    lock.acquire("a")
    lock.acquire("b")
    assert lock.active_lock_count() == 2
