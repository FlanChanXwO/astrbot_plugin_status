from __future__ import annotations

from typing import Any

from astrbot.api import logger as _astrbot_logger


class StatusLogger:
    """AstrBot 日志包装器，统一添加插件前缀。"""

    PREFIX = "[astrbot_plugin_status] "

    def _add_prefix(self, msg: object) -> str:
        """为日志消息添加插件名前缀，便于运行时筛选。"""
        return self.PREFIX + str(msg)

    @staticmethod
    def _with_stacklevel(kwargs: dict[str, Any]) -> dict[str, Any]:
        """保留真实调用位置，避免日志定位停在包装器内部。"""
        copied = dict(kwargs)
        if "stacklevel" not in copied:
            copied["stacklevel"] = 2
        return copied

    def debug(self, msg: object, *args: Any, **kwargs: Any) -> None:
        _astrbot_logger.debug(
            self._add_prefix(msg), *args, **self._with_stacklevel(kwargs)
        )

    def info(self, msg: object, *args: Any, **kwargs: Any) -> None:
        _astrbot_logger.info(
            self._add_prefix(msg), *args, **self._with_stacklevel(kwargs)
        )

    def warning(self, msg: object, *args: Any, **kwargs: Any) -> None:
        _astrbot_logger.warning(
            self._add_prefix(msg), *args, **self._with_stacklevel(kwargs)
        )

    def error(self, msg: object, *args: Any, **kwargs: Any) -> None:
        _astrbot_logger.error(
            self._add_prefix(msg), *args, **self._with_stacklevel(kwargs)
        )

    def exception(self, msg: object, *args: Any, **kwargs: Any) -> None:
        _astrbot_logger.exception(
            self._add_prefix(msg), *args, **self._with_stacklevel(kwargs)
        )

    def critical(self, msg: object, *args: Any, **kwargs: Any) -> None:
        _astrbot_logger.critical(
            self._add_prefix(msg), *args, **self._with_stacklevel(kwargs)
        )


_instance: StatusLogger | None = None


def get_logger() -> StatusLogger:
    """获取插件日志记录器单例。"""
    global _instance
    if _instance is None:
        _instance = StatusLogger()
    return _instance


logger = get_logger()
