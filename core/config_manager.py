from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .constants import (
    DEFAULT_BOT_NAME,
    DEFAULT_COMMENT_PROMPT,
    DEFAULT_VISION_PROMPT,
)


@dataclass(slots=True, frozen=True)
class LLMAnalysisConfig:
    """LLM 分析相关配置，供命令处理流程直接读取。"""

    enabled: bool
    vision_provider_id: str
    comment_provider_id: str
    vision_prompt: str
    comment_prompt: str


class ConfigManager:
    """集中解析 status 插件配置，避免业务逻辑散落直接读取 AstrBotConfig。"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.auto_use_current_name = True
        self.bot_name = DEFAULT_BOT_NAME
        self.banner_paths: list[str] = []
        self.llm_analysis = LLMAnalysisConfig(
            enabled=False,
            vision_provider_id="",
            comment_provider_id="",
            vision_prompt=DEFAULT_VISION_PROMPT,
            comment_prompt=DEFAULT_COMMENT_PROMPT,
        )

    def load(self) -> None:
        """加载并校验全部配置字段。"""
        self.auto_use_current_name = self._get_bool("auto_use_current_name", True)
        self.bot_name = self._get_non_empty_string("bot_name", DEFAULT_BOT_NAME)
        self.banner_paths = self._get_string_list("banner_image")
        self.llm_analysis = LLMAnalysisConfig(
            enabled=self._get_bool("enable_llm_analysis", False),
            vision_provider_id=self._get_string("vision_provider_id").strip(),
            comment_provider_id=self._get_string("comment_provider_id").strip(),
            vision_prompt=self._get_non_empty_string(
                "vision_prompt",
                DEFAULT_VISION_PROMPT,
            ),
            comment_prompt=self._get_non_empty_string(
                "comment_prompt",
                DEFAULT_COMMENT_PROMPT,
            ),
        )

    def _get_bool(self, key: str, default: bool) -> bool:
        value = self.config.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
        return default

    def _get_string(self, key: str, default: str = "") -> str:
        value = self.config.get(key, default)
        return value if isinstance(value, str) else default

    def _get_non_empty_string(self, key: str, default: str) -> str:
        value = self._get_string(key, default).strip()
        return value or default

    def _get_string_list(self, key: str) -> list[str]:
        value = self.config.get(key, [])
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str) and item.strip()]
