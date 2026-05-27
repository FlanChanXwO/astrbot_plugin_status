from __future__ import annotations

from tests.support import (
    create_core_package,
    install_astrbot_stubs,
    load_core_module,
)

PACKAGE_NAME = "status_core_utils_tests"

install_astrbot_stubs()
create_core_package(PACKAGE_NAME)

constants_module = load_core_module(PACKAGE_NAME, "constants")
load_core_module(PACKAGE_NAME, "logger")
utils_module = load_core_module(PACKAGE_NAME, "utils")

MAX_RENDERED_BOT_NAME_LENGTH = constants_module.MAX_RENDERED_BOT_NAME_LENGTH
truncate_middle = utils_module.truncate_middle


def test_short_text_is_not_truncated() -> None:
    assert truncate_middle("AstrBot", MAX_RENDERED_BOT_NAME_LENGTH) == "AstrBot"


def test_long_text_uses_middle_ellipsis() -> None:
    truncated = truncate_middle(
        "SuperLongAstrBotDisplayName",
        MAX_RENDERED_BOT_NAME_LENGTH,
    )

    assert truncated == "SuperL...ayName"
    assert len(truncated) == MAX_RENDERED_BOT_NAME_LENGTH
    assert "..." in truncated


def test_tiny_max_length_returns_only_dots() -> None:
    assert truncate_middle("AstrBot", 3) == "..."


def test_zero_or_negative_max_length_returns_empty_text() -> None:
    assert truncate_middle("AstrBot", 0) == ""
    assert truncate_middle("AstrBot", -1) == ""
