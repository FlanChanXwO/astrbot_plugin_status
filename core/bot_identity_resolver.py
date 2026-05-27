from __future__ import annotations

from collections.abc import Iterable
from inspect import isawaitable
from typing import Any

from .config_manager import ConfigManager
from .logger import logger


class BotIdentityResolver:
    """从 AstrBot 上下文和事件中解析机器人状态卡显示名。"""

    _PLATFORM_NAME_PATHS: dict[str, tuple[tuple[str, ...], ...]] = {
        "kook": (
            ("client", "bot_nickname"),
            ("client", "bot_username"),
        ),
        "mattermost": (("bot_username",),),
        "misskey": (("_bot_username",),),
        "discord": (
            ("client", "user", "display_name"),
            ("client", "user", "name"),
            ("client", "user", "global_name"),
        ),
        "telegram": (
            ("client", "username"),
            ("application", "bot", "username"),
        ),
    }

    def __init__(self, context: Any, config_manager: ConfigManager) -> None:
        self.context = context
        self.config_manager = config_manager

    async def resolve(self, event: Any | None = None) -> str:
        """优先平台机器人昵称/用户名，再回退 platform_id，最后使用配置名。"""
        if not self.config_manager.auto_use_current_name:
            return self.config_manager.bot_name

        platform_name = self._get_event_platform_name(event)
        platform_id = self._get_event_platform_id(event)
        platform = self._find_platform_instance(platform_name, platform_id)
        if not platform_name and platform is not None:
            platform_name = self._get_platform_name(platform)

        if platform_name == "aiocqhttp":
            name = await self._resolve_aiocqhttp_name(event, platform)
        else:
            name = self._resolve_platform_name(platform_name, platform)
        if name:
            return name
        if platform_id:
            return platform_id

        return self.config_manager.bot_name

    def _resolve_platform_name(self, platform_name: str, platform: Any | None) -> str:
        if platform is None:
            return ""

        for path in self._PLATFORM_NAME_PATHS.get(platform_name, ()):
            name = self._get_path_text(platform, path)
            if name:
                return name

        return ""

    async def _resolve_aiocqhttp_name(
        self,
        event: Any | None,
        platform: Any | None,
    ) -> str:
        bot = self._get_aiocqhttp_bot(event, platform)
        if bot is None:
            return ""

        call_action = getattr(bot, "call_action", None)
        if not callable(call_action):
            return ""

        try:
            # OneBot v11 的 get_login_info 返回机器人自身账号信息。
            result = call_action(action="get_login_info")
            if isawaitable(result):
                result = await result
        except Exception as exc:
            logger.warning(f"获取 aiocqhttp 机器人名称失败: {exc}")
            return ""

        return self._get_result_text(result, "nickname")

    def _find_platform_instance(
        self,
        platform_name: str,
        platform_id: str,
    ) -> Any | None:
        platform = self._get_platform_inst(platform_id)
        if platform is not None:
            return platform

        for platform in self._iter_platform_instances():
            meta = self._call_meta(platform)
            meta_id = self._get_text(getattr(meta, "id", ""))
            meta_name = self._get_text(getattr(meta, "name", ""))
            if platform_id and meta_id == platform_id:
                return platform
            if not platform_id and platform_name and meta_name == platform_name:
                return platform
        return None

    def _get_platform_name(self, platform: Any) -> str:
        meta = self._call_meta(platform)
        return self._get_text(getattr(meta, "name", ""))

    def _get_platform_inst(self, platform_id: str) -> Any | None:
        if not platform_id:
            return None
        getter = getattr(self.context, "get_platform_inst", None)
        if not callable(getter):
            return None
        return getter(platform_id)

    def _iter_platform_instances(self) -> Iterable[Any]:
        platform_manager = getattr(self.context, "platform_manager", None)
        platforms = getattr(platform_manager, "platform_insts", ())
        if not isinstance(platforms, Iterable):
            return ()
        return platforms

    @staticmethod
    def _call_meta(platform: Any) -> Any | None:
        meta = getattr(platform, "meta", None)
        if callable(meta):
            return meta()
        return getattr(platform, "metadata", None)

    @classmethod
    def _get_event_platform_name(cls, event: Any | None) -> str:
        name = cls._call_getter_text(event, "get_platform_name")
        if name:
            return name
        meta = getattr(event, "platform_meta", None)
        return cls._get_text(getattr(meta, "name", ""))

    @classmethod
    def _get_event_platform_id(cls, event: Any | None) -> str:
        platform_id = cls._call_getter_text(event, "get_platform_id")
        if platform_id:
            return platform_id
        meta = getattr(event, "platform_meta", None)
        return cls._get_text(getattr(meta, "id", ""))

    @classmethod
    def _get_path_text(cls, obj: Any, path: tuple[str, ...]) -> str:
        current = obj
        for attr in path:
            current = getattr(current, attr, None)
            if current is None:
                return ""
        return cls._get_text(current)

    @classmethod
    def _call_getter_text(cls, obj: Any | None, getter_name: str) -> str:
        getter = getattr(obj, getter_name, None)
        if not callable(getter):
            return ""
        return cls._get_text(getter())

    @staticmethod
    def _get_aiocqhttp_bot(event: Any | None, platform: Any | None) -> Any | None:
        event_bot = getattr(event, "bot", None)
        if event_bot is not None:
            return event_bot
        return getattr(platform, "bot", None)

    @classmethod
    def _get_result_text(cls, value: Any, key: str) -> str:
        if isinstance(value, dict):
            return cls._get_text(value.get(key))
        return cls._get_text(getattr(value, key, ""))

    @staticmethod
    def _get_text(value: Any) -> str:
        text = str(value or "").strip()
        return text
