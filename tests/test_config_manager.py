from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PACKAGE_NAME = "status_core_for_tests"
package = types.ModuleType(PACKAGE_NAME)
package.__path__ = [str(ROOT / "core")]
sys.modules[PACKAGE_NAME] = package

CONSTANTS_SPEC = importlib.util.spec_from_file_location(
    f"{PACKAGE_NAME}.constants",
    ROOT / "core" / "constants.py",
)
assert CONSTANTS_SPEC is not None
assert CONSTANTS_SPEC.loader is not None
status_constants = importlib.util.module_from_spec(CONSTANTS_SPEC)
sys.modules[CONSTANTS_SPEC.name] = status_constants
CONSTANTS_SPEC.loader.exec_module(status_constants)

CONFIG_SPEC = importlib.util.spec_from_file_location(
    f"{PACKAGE_NAME}.config_manager",
    ROOT / "core" / "config_manager.py",
)
assert CONFIG_SPEC is not None
assert CONFIG_SPEC.loader is not None
status_config_manager = importlib.util.module_from_spec(CONFIG_SPEC)
sys.modules[CONFIG_SPEC.name] = status_config_manager
CONFIG_SPEC.loader.exec_module(status_config_manager)

ConfigManager = status_config_manager.ConfigManager
DEFAULT_BOT_NAME = status_config_manager.DEFAULT_BOT_NAME
DEFAULT_COMMENT_PROMPT = status_config_manager.DEFAULT_COMMENT_PROMPT
DEFAULT_VISION_PROMPT = status_config_manager.DEFAULT_VISION_PROMPT


class FakeEvent:
    def __init__(self, sender_name: str = "", platform_id: str = "") -> None:
        self.sender_name = sender_name
        self.platform_id = platform_id

    def get_sender_name(self) -> str:
        return self.sender_name

    def get_platform_id(self) -> str:
        return self.platform_id


def test_config_manager_loads_defaults() -> None:
    manager = ConfigManager({})
    manager.load()

    assert manager.auto_use_current_name is True
    assert manager.bot_name == DEFAULT_BOT_NAME
    assert manager.banner_paths == []
    assert manager.llm_analysis.enabled is False
    assert manager.llm_analysis.vision_provider_id == ""
    assert manager.llm_analysis.comment_provider_id == ""
    assert manager.llm_analysis.vision_prompt == DEFAULT_VISION_PROMPT
    assert manager.llm_analysis.comment_prompt == DEFAULT_COMMENT_PROMPT


def test_config_manager_normalizes_valid_values() -> None:
    manager = ConfigManager(
        {
            "auto_use_current_name": "false",
            "bot_name": "  酒狐  ",
            "banner_image": [
                "/tmp/banner-a.png",
                "",
                123,
                "/tmp/banner-b.jpg",
            ],
            "enable_llm_analysis": "true",
            "vision_provider_id": "  vlm-provider  ",
            "comment_provider_id": "  text-provider  ",
            "vision_prompt": "  描述状态图  ",
            "comment_prompt": "  总结：{description}  ",
        }
    )
    manager.load()

    assert manager.auto_use_current_name is False
    assert manager.bot_name == "酒狐"
    assert manager.banner_paths == ["/tmp/banner-a.png", "/tmp/banner-b.jpg"]
    assert manager.llm_analysis.enabled is True
    assert manager.llm_analysis.vision_provider_id == "vlm-provider"
    assert manager.llm_analysis.comment_provider_id == "text-provider"
    assert manager.llm_analysis.vision_prompt == "描述状态图"
    assert manager.llm_analysis.comment_prompt == "总结：{description}"


def test_config_manager_falls_back_for_invalid_types() -> None:
    manager = ConfigManager(
        {
            "auto_use_current_name": object(),
            "bot_name": 123,
            "banner_image": "/tmp/banner.png",
            "enable_llm_analysis": object(),
            "vision_provider_id": [],
            "comment_provider_id": {},
            "vision_prompt": "",
            "comment_prompt": "",
        }
    )
    manager.load()

    assert manager.auto_use_current_name is True
    assert manager.bot_name == DEFAULT_BOT_NAME
    assert manager.banner_paths == []
    assert manager.llm_analysis.enabled is False
    assert manager.llm_analysis.vision_provider_id == ""
    assert manager.llm_analysis.comment_provider_id == ""
    assert manager.llm_analysis.vision_prompt == DEFAULT_VISION_PROMPT
    assert manager.llm_analysis.comment_prompt == DEFAULT_COMMENT_PROMPT


def test_resolve_bot_name_uses_sender_name_then_platform_id() -> None:
    manager = ConfigManager({"bot_name": "配置名"})
    manager.load()

    assert manager.resolve_bot_name(FakeEvent(sender_name="发送者")) == "发送者"
    assert (
        manager.resolve_bot_name(FakeEvent(sender_name="", platform_id="platform-a"))
        == "platform-a"
    )
    assert manager.resolve_bot_name(FakeEvent()) == "配置名"


def test_resolve_bot_name_respects_manual_name_mode() -> None:
    manager = ConfigManager(
        {
            "auto_use_current_name": False,
            "bot_name": "手动名",
        }
    )
    manager.load()

    assert manager.resolve_bot_name(FakeEvent(sender_name="发送者")) == "手动名"
