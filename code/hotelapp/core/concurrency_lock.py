"""并发锁组件。

对应 UML 类图系统支撑模块中的 ``ConcurrencyLock``。当多个用户
同时争抢最后一套房时（REQ-008），需要保证只有一个请求能进入
库存扣减临界区。这里以 ``threading`` 为基础，为每个
"房型 + 日期"资源维护一把可重入锁，并采用非阻塞获取：拿不到
锁的请求立即失败，从而模拟数据库行锁/分布式锁的抢占语义。
"""

import threading
from contextlib import contextmanager


class ConcurrencyLock:
    """按资源键管理的并发锁管理器。"""

    def __init__(self) -> None:
        # 资源键 -> 锁对象；用一把元锁保护该字典本身的并发访问。
        self._locks = {}
        self._meta_lock = threading.Lock()

    def _get_lock(self, resource_key: str) -> threading.Lock:
        """获取（必要时创建）某资源对应的锁。"""
        with self._meta_lock:
            if resource_key not in self._locks:
                self._locks[resource_key] = threading.Lock()
            return self._locks[resource_key]

    @staticmethod
    def build_key(room_type_id: int, target_date) -> str:
        """根据房型与日期构造资源键。"""
        return f"room:{room_type_id}:date:{target_date.isoformat()}"

    def acquire(self, resource_key: str, blocking: bool = False) -> bool:
        """尝试获取资源锁，成功返回 True；非阻塞模式下被占用则返回 False。"""
        lock = self._get_lock(resource_key)
        return lock.acquire(blocking=blocking)

    def release(self, resource_key: str) -> None:
        """释放资源锁。仅允许释放已存在且被持有的锁。"""
        lock = self._locks.get(resource_key)
        if lock is None:
            raise KeyError(f"资源锁不存在: {resource_key}")
        lock.release()

    @contextmanager
    def try_lock(self, resource_key: str):
        """上下文管理器：进入时非阻塞抢锁，退出时自动释放。

        用法::

            with lock.try_lock(key) as locked:
                if not locked:
                    raise RuntimeError("资源已被占用")
                # 临界区：查询并扣减库存
        """
        held = self.acquire(resource_key)
        try:
            yield held
        finally:
            if held:
                self.release(resource_key)

    def active_lock_count(self) -> int:
        """当前管理的锁数量，主要用于监控与测试。"""
        return len(self._locks)
