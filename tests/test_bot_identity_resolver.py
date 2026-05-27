from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from tests.support import (
    create_core_package,
    install_astrbot_stubs,
    load_core_module,
)

pytestmark = pytest.mark.asyncio

PACKAGE_NAME = "status_core_identity_tests"

install_astrbot_stubs()
create_core_package(PACKAGE_NAME)

load_core_module(PACKAGE_NAME, "constants")
load_core_module(PACKAGE_NAME, "logger")
config_module = load_core_module(PACKAGE_NAME, "config_manager")
resolver_module = load_core_module(PACKAGE_NAME, "bot_identity_resolver")

ConfigManager = config_module.ConfigManager
BotIdentityResolver = resolver_module.BotIdentityResolver


class FakeEvent:
    def __init__(
        self,
        *,
        platform_name: str,
        platform_id: str,
        self_id: str = "event-self-id",
        bot: Any | None = None,
    ) -> None:
        self.platform_name = platform_name
        self.platform_id = platform_id
        self.self_id = self_id
        self.bot = bot

    def get_platform_name(self) -> str:
        return self.platform_name

    def get_platform_id(self) -> str:
        return self.platform_id

    def get_self_id(self) -> str:
        raise AssertionError("BotIdentityResolver 不应读取 self_id 作为名称回退")

    def get_sender_name(self) -> str:
        raise AssertionError("BotIdentityResolver 不应读取发送者名称")


class FakePlatform:
    def __init__(
        self,
        *,
        platform_name: str,
        platform_id: str,
        attrs: dict[str, Any],
    ) -> None:
        self.metadata = SimpleNamespace(name=platform_name, id=platform_id)
        for key, value in attrs.items():
            setattr(self, key, value)

    def meta(self) -> SimpleNamespace:
        return self.metadata


class FakeContext:
    def __init__(self, platforms: list[FakePlatform]) -> None:
        self.platform_manager = SimpleNamespace(platform_insts=platforms)


class FakeContextWithGetter(FakeContext):
    def __init__(
        self,
        platforms: list[FakePlatform],
        platform_by_id: dict[str, FakePlatform],
    ) -> None:
        super().__init__(platforms)
        self.platform_by_id = platform_by_id

    def get_platform_inst(self, platform_id: str) -> FakePlatform | None:
        return self.platform_by_id.get(platform_id)


class FakeOneBot:
    def __init__(
        self,
        *,
        nickname: str = "OneBot 昵称",
        should_raise: bool = False,
    ) -> None:
        self.nickname = nickname
        self.should_raise = should_raise
        self.call_count = 0

    async def call_action(self, *, action: str) -> dict[str, str]:
        self.call_count += 1
        assert action == "get_login_info"
        if self.should_raise:
            raise RuntimeError("onebot api failed")
        return {"nickname": self.nickname}


def _manager(
    *, bot_name: str = "配置名", auto_use_current_name: bool = True
) -> ConfigManager:
    manager = ConfigManager(
        {
            "auto_use_current_name": auto_use_current_name,
            "bot_name": bot_name,
        }
    )
    manager.load()
    return manager


async def _resolve(
    *,
    platform_name: str,
    platform_attrs: dict[str, Any],
    event_self_id: str = "event-self-id",
    platform_id: str = "platform-a",
    event_bot: Any | None = None,
) -> str:
    platform = FakePlatform(
        platform_name=platform_name,
        platform_id=platform_id,
        attrs=platform_attrs,
    )
    resolver = BotIdentityResolver(FakeContext([platform]), _manager())
    return await resolver.resolve(
        FakeEvent(
            platform_name=platform_name,
            platform_id=platform_id,
            self_id=event_self_id,
            bot=event_bot,
        )
    )


@pytest.mark.parametrize(
    ("platform_name", "platform_attrs", "expected"),
    [
        (
            "kook",
            {
                "client": SimpleNamespace(
                    bot_nickname="KOOK 昵称",
                    bot_username="kook-user",
                )
            },
            "KOOK 昵称",
        ),
        ("mattermost", {"bot_username": "mattermost-bot"}, "mattermost-bot"),
        ("misskey", {"_bot_username": "misskey-bot"}, "misskey-bot"),
        (
            "discord",
            {
                "client": SimpleNamespace(
                    user=SimpleNamespace(display_name="Discord Bot")
                )
            },
            "Discord Bot",
        ),
        (
            "telegram",
            {"client": SimpleNamespace(username="telegram_bot")},
            "telegram_bot",
        ),
    ],
)
async def test_resolve_uses_platform_instance_name_first(
    platform_name: str,
    platform_attrs: dict[str, Any],
    expected: str,
) -> None:
    assert (
        await _resolve(
            platform_name=platform_name,
            platform_attrs=platform_attrs,
        )
        == expected
    )


async def test_kook_falls_back_from_nickname_to_username() -> None:
    assert (
        await _resolve(
            platform_name="kook",
            platform_attrs={
                "client": SimpleNamespace(bot_nickname="", bot_username="kook-user")
            },
        )
        == "kook-user"
    )


async def test_resolve_prefers_context_get_platform_inst() -> None:
    event = FakeEvent(platform_name="telegram", platform_id="platform-a")
    listed_platform = FakePlatform(
        platform_name="telegram",
        platform_id="platform-a",
        attrs={"client": SimpleNamespace(username="listed-bot")},
    )
    current_platform = FakePlatform(
        platform_name="telegram",
        platform_id="platform-a",
        attrs={"client": SimpleNamespace(username="current-bot")},
    )
    resolver = BotIdentityResolver(
        FakeContextWithGetter([listed_platform], {"platform-a": current_platform}),
        _manager(),
    )

    assert await resolver.resolve(event) == "current-bot"


async def test_resolve_uses_platform_meta_name_when_event_name_is_missing() -> None:
    event = FakeEvent(platform_name="", platform_id="platform-a")
    current_platform = FakePlatform(
        platform_name="telegram",
        platform_id="platform-a",
        attrs={"client": SimpleNamespace(username="current-bot")},
    )
    resolver = BotIdentityResolver(
        FakeContextWithGetter([], {"platform-a": current_platform}),
        _manager(),
    )

    assert await resolver.resolve(event) == "current-bot"


async def test_aiocqhttp_uses_onebot_login_nickname_from_event_bot() -> None:
    bot = FakeOneBot(nickname="OneBot 机器人")

    assert (
        await _resolve(
            platform_name="aiocqhttp",
            platform_attrs={},
            event_bot=bot,
        )
        == "OneBot 机器人"
    )
    assert bot.call_count == 1


async def test_aiocqhttp_uses_onebot_login_nickname_from_platform_bot() -> None:
    bot = FakeOneBot(nickname="平台机器人")

    assert (
        await _resolve(
            platform_name="aiocqhttp",
            platform_attrs={"bot": bot},
        )
        == "平台机器人"
    )
    assert bot.call_count == 1


async def test_aiocqhttp_falls_back_to_platform_id_for_empty_login_nickname() -> None:
    assert (
        await _resolve(
            platform_name="aiocqhttp",
            platform_attrs={},
            event_bot=FakeOneBot(nickname=""),
        )
        == "platform-a"
    )


async def test_aiocqhttp_falls_back_to_platform_id_when_login_info_fails() -> None:
    assert (
        await _resolve(
            platform_name="aiocqhttp",
            platform_attrs={},
            event_bot=FakeOneBot(should_raise=True),
        )
        == "platform-a"
    )


async def test_unknown_platform_does_not_use_unverified_common_name_fields() -> None:
    assert (
        await _resolve(
            platform_name="unknown",
            platform_attrs={"bot_username": "generic-bot-name"},
        )
        == "platform-a"
    )


async def test_resolve_falls_back_to_configured_bot_name() -> None:
    resolver = BotIdentityResolver(FakeContext([]), _manager(bot_name="配置兜底名"))

    assert (
        await resolver.resolve(
            FakeEvent(platform_name="telegram", platform_id="", self_id="")
        )
        == "配置兜底名"
    )


async def test_resolve_respects_manual_config_name() -> None:
    bot = FakeOneBot(nickname="不应调用")
    resolver = BotIdentityResolver(
        FakeContext(
            [
                FakePlatform(
                    platform_name="aiocqhttp",
                    platform_id="platform-a",
                    attrs={"bot": bot},
                )
            ]
        ),
        _manager(bot_name="手动名", auto_use_current_name=False),
    )

    assert (
        await resolver.resolve(
            FakeEvent(platform_name="aiocqhttp", platform_id="platform-a", bot=bot)
        )
        == "手动名"
    )
    assert bot.call_count == 0
