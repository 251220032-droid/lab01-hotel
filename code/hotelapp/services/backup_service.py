"""数据库备份服务。

对应 UML 类图系统支撑模块中的 ``BackupService``，落实 REQ-015
的每日定时备份与可靠性约束。提供立即备份、备份校验与失败
告警：备份文件按时间戳命名并复制到独立目录，校验通过后返回
备份路径，失败则通过异常日志管理器记录。
"""

import os
import shutil
from datetime import datetime


class BackupError(Exception):
    """备份相关业务异常。"""


class BackupService:
    """执行数据库文件的每日备份、校验与告警。"""

    def __init__(self, source_path: str, backup_dir: str,
                 log_manager=None) -> None:
        self._source_path = source_path
        self._backup_dir = backup_dir
        self._log_manager = log_manager

    @property
    def backup_dir(self) -> str:
        """备份目录。"""
        return self._backup_dir

    def run_daily_backup(self, now: datetime = None) -> str:
        """立即执行一次备份，返回备份文件路径。"""
        current = now or datetime.now()
        if not os.path.exists(self._source_path):
            self.alert_on_failure("源数据库文件不存在")
            raise BackupError("源数据库文件不存在")
        os.makedirs(self._backup_dir, exist_ok=True)
        stamp = current.strftime("%Y%m%d_%H%M%S")
        target = os.path.join(self._backup_dir, f"backup_{stamp}.json")
        shutil.copy2(self._source_path, target)
        if not self.verify_backup(target):
            self.alert_on_failure("备份文件校验失败")
            raise BackupError("备份文件校验失败")
        return target

    def verify_backup(self, backup_path: str) -> bool:
        """校验备份文件存在且非空、字节数与源文件一致。"""
        if not os.path.exists(backup_path):
            return False
        if os.path.getsize(backup_path) == 0:
            return False
        return os.path.getsize(backup_path) == os.path.getsize(self._source_path)

    def list_backups(self) -> list:
        """列出已有备份文件，按时间倒序。"""
        if not os.path.exists(self._backup_dir):
            return []
        files = [
            os.path.join(self._backup_dir, name)
            for name in os.listdir(self._backup_dir)
            if name.startswith("backup_")
        ]
        return sorted(files, reverse=True)

    def alert_on_failure(self, reason: str) -> None:
        """备份失败时记录异常日志，供运维排查。"""
        if self._log_manager is not None:
            self._log_manager.add("数据库备份失败", reason)
