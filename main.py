from __future__ import annotations

from pathlib import Path

from astrbot.api import AstrBotConfig
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, StarTools
from astrbot.core.provider.register import llm_tools

from .core import ConfigManager, HtmlRender, StatusService
from .core.constants import STATUS_TOOL_DESCRIPTION, STATUS_TOOL_NAME


class StatusPlugin(Star):
    """系统状态卡插件入口，负责框架生命周期和命令注册。"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.base_dir = Path(__file__).parent
        self.config_manager = ConfigManager(config)
        self.config_manager.load()
        self.plugin_data_dir = StarTools.get_data_dir(self.name)
        self.html_renderer = HtmlRender(
            context=context,
            config_manager=self.config_manager,
            base_dir=self.base_dir,
            plugin_data_dir=self.plugin_data_dir,
            html_render=self.html_render,
        )
        self.status_service = StatusService(
            context=context,
            config_manager=self.config_manager,
            html_renderer=self.html_renderer,
        )

    async def initialize(self) -> None:
        """Register LLM tool for Agent to fetch status image."""
        llm_tools.add_func(
            name=STATUS_TOOL_NAME,
            func_args=[],
            desc=STATUS_TOOL_DESCRIPTION,
            handler=self.status_service.get_status_tool_handler,
        )
        tool = llm_tools.get_func(STATUS_TOOL_NAME)
        if tool:
            tool.handler_module_path = __name__

    async def terminate(self) -> None:
        """Unregister LLM tool on plugin disable."""
        llm_tools.remove_func(STATUS_TOOL_NAME)

    @filter.command("status", alias={"状态"})
    async def show_status(self, event: AstrMessageEvent):
        """返回状态图片"""
        async for result in self.status_service.show_status(event):
            yield result
