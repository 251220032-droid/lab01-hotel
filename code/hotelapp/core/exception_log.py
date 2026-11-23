"""异常日志组件。

对应 UML 类图系统支撑模块中的 ``ExceptionLog``，用于在支付或
退款网关异常时记录错误上下文，并标记是否需要人工重试
（REQ-011、REQ-010）。除日志实体外，本模块还提供一个管理
器，负责新增、查询与更新重试状态。
"""

from datetime import datetime


class ExceptionLog:
    """单条异常日志记录。"""

    def __init__(self, log_id: int, error_message: str, context: str,
                 retry_status: str = "待人工重试",
                 created_at: datetime = None) -> None:
        self._log_id = log_id
        self._error_message = error_message
        self._context = context
        self._retry_status = retry_status
        self._created_at = created_at or datetime.now()

    @property
    def log_id(self) -> int:
        """日志唯一标识。"""
        return self._log_id

    @property
    def error_message(self) -> str:
        """错误信息。"""
        return self._error_message

    @property
    def context(self) -> str:
        """发生错误时的上下文信息。"""
        return self._context

    @property
    def retry_status(self) -> str:
        """重试状态。"""
        return self._retry_status

    @property
    def created_at(self) -> datetime:
        """记录时间。"""
        return self._created_at

    def mark_resolved(self) -> None:
        """人工重试成功后标记为已处理。"""
        self._retry_status = "已处理"

    def to_dict(self) -> dict:
        """序列化日志。"""
        return {
            "log_id": self._log_id,
            "error_message": self._error_message,
            "context": self._context,
            "retry_status": self._retry_status,
            "created_at": self._created_at.isoformat(timespec="seconds"),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExceptionLog":
        """根据字典重建日志。"""
        return cls(
            data["log_id"], data["error_message"], data["context"],
            data.get("retry_status", "待人工重试"),
            datetime.fromisoformat(data["created_at"]),
        )


class ExceptionLogManager:
    """管理全部异常日志，提供新增、检索与重试状态更新。"""

    def __init__(self) -> None:
        self._logs = []
        self._next_id = 1

    @property
    def logs(self) -> list:
        """全部日志，按时间顺序排列。"""
        return self._logs

    def add(self, error_message: str, context: str) -> ExceptionLog:
        """新增一条异常日志并返回它。"""
        log = ExceptionLog(self._next_id, error_message, context)
        self._logs.append(log)
        self._next_id += 1
        return log

    def find(self, log_id: int) -> ExceptionLog:
        """按标识查找日志。"""
        for log in self._logs:
            if log.log_id == log_id:
                return log
        return None

    def pending_logs(self) -> list:
        """返回仍待人工重试的日志。"""
        return [log for log in self._logs if log.retry_status == "待人工重试"]

    def resolve(self, log_id: int) -> bool:
        """将指定日志标记为已处理，成功返回 True。"""
        log = self.find(log_id)
        if log:
            log.mark_resolved()
            return True
        return False

    def to_list(self) -> list:
        """序列化为日志字典列表。"""
        return [log.to_dict() for log in self._logs]

    def load_list(self, data: list) -> None:
        """从字典列表恢复日志，并校正下一个可用标识。"""
        self._logs = [ExceptionLog.from_dict(item) for item in data]
        max_id = max((log.log_id for log in self._logs), default=0)
        self._next_id = max_id + 1
