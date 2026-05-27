from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_status_service_delegates_rendering_to_html_render() -> None:
    source = (ROOT / "core/status_service.py").read_text(encoding="utf-8-sig")

    assert "from .data_source import SystemDataSource" not in source
    assert "build_render_data" not in source
    assert "render_status_image" in source
    assert "build_status_text" in source
    assert "self.html_renderer.render_status_image" in source
    assert "self.html_renderer.build_status_text" in source


def test_html_render_owns_status_data_and_rendering() -> None:
    source = (ROOT / "core/html_render.py").read_text(encoding="utf-8-sig")
    init_source = (ROOT / "core/__init__.py").read_text(encoding="utf-8-sig")

    assert "class HtmlRender" in source
    assert "from .data_source import SystemDataSource" in source
    assert "async def render_status_image" in source
    assert "async def build_status_text" in source
    assert "async def build_render_data" in source
    assert "build_render_data" not in init_source


def test_core_modules_use_prefixed_logger() -> None:
    logger_source = (ROOT / "core/logger.py").read_text(encoding="utf-8-sig")

    assert 'PREFIX = "[astrbot_plugin_status] "' in logger_source

    for path in (ROOT / "core").glob("*.py"):
        source = path.read_text(encoding="utf-8-sig")
        if path.name == "logger.py":
            assert "from astrbot.api import logger as _astrbot_logger" in source
            continue
        assert "from astrbot.api import logger" not in source
        assert "[Status]" not in source
