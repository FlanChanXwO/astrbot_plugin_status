from __future__ import annotations

import logging
import random
from dataclasses import asdict
from pathlib import Path

import mcp.types

from astrbot.api import AstrBotConfig
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star
from astrbot.core.exceptions import ProviderNotFoundError
from astrbot.core.provider.register import llm_tools
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from .data_source import SystemDataSource
from .models import StatusPayload
from .utils import get_image_data_uri, image_url_to_base64, inline_fonts_in_css

logger = logging.getLogger(__name__)

class StatusPlugin(Star):
    """
    一个用于渲染系统状态卡的插件。
    """
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context, config)
        self.base_dir = Path(__file__).parent
        self.config = config
        self.context = context
        self.plugin_data_dir = Path(get_astrbot_data_path()) / "plugin_data" / self.name
        self.template_path = self.base_dir / "templates" / "main.html"
        self.css_path = self.base_dir / "templates" / "res" / "css" / "style.css"
        self.character_dir = self.base_dir / "templates" / "res" / "image" / "character"
        self.default_banner_dir = self.base_dir / "templates" / "res" / "image" / "banner"
        self.render_options = {
            "full_page": True,
            "type": "png",
            "scale": "device",
            "device_scale_factor": 2.0
        }
        self.data_source = SystemDataSource(context, self.base_dir)
        self.bot_name = config.get("bot_name")
        self.banner_paths = config.get("banner_image", [])

    async def initialize(self) -> None:
        """Register LLM tool for Agent to fetch status image."""
        llm_tools.add_func(
            name="astrbot_get_system_status",
            func_args=[],
            desc=(
                "Get the current system status image including CPU, RAM, SWAP, DISK, "
                "network usage and uptime. Call this when user asks about system status, "
                "server status, or machine status."
            ),
            handler=self._get_status_tool_handler,
        )
        tool = llm_tools.get_func("astrbot_get_system_status")
        if tool:
            tool.handler_module_path = __name__

    async def terminate(self) -> None:
        """Unregister LLM tool on plugin disable."""
        llm_tools.remove_func("astrbot_get_system_status")

    async def _get_status_tool_handler(self, event: AstrMessageEvent) -> mcp.types.CallToolResult:
        """LLM tool handler: render status image and return as base64 for LLM to view."""
        try:
            html_content, payload = self._build_render_data(event)
            payload_dict = asdict(payload)
            image_url = await self.html_render(
                html_content,
                payload_dict,
                return_url=True,
                options=self.render_options,
            )
        except Exception:
            logger.exception("Status image render failed in LLM tool")
            return mcp.types.CallToolResult(
                content=[mcp.types.TextContent(type="text", text="状态图片渲染失败。")]
            )
        img_b64 = await image_url_to_base64(image_url)
        if not img_b64:
            return mcp.types.CallToolResult(
                content=[mcp.types.TextContent(type="text", text="无法获取状态图片数据。")]
            )
        return mcp.types.CallToolResult(
            content=[
                mcp.types.ImageContent(
                    type="image",
                    data=img_b64,
                    mimeType="image/png",
                )
            ]
        )

    @filter.regex(r"^/?(状态|status)$")
    async def show_status(self, event: AstrMessageEvent):
        """返回状态图片"""
        try:
            html_content, payload = self._build_render_data(event)
            payload_dict = asdict(payload)
            image_url = await self.html_render(
                html_content,
                payload_dict,
                return_url=True,
                options=self.render_options,
            )
        except Exception:
            logger.exception("状态图片渲染失败")
            yield event.plain_result("状态图片渲染失败，请稍后再试。")
            return
        yield event.image_result(image_url)

        enable_llm = self.config.get("enable_llm_analysis", False)
        if enable_llm:
            try:
                prov_id = await self.context.get_current_chat_provider_id(
                    event.unified_msg_origin
                )
                prompt = self.config.get(
                    "llm_analysis_prompt",
                    "请简要分析这张系统状态图片，用一两句话总结 CPU、内存、磁盘等关键信息。",
                )
                llm_resp = await self.context.llm_generate(
                    chat_provider_id=prov_id,
                    prompt=prompt,
                    image_urls=[image_url],
                )
                if llm_resp and llm_resp.completion_text:
                    yield event.plain_result(llm_resp.completion_text)
            except ProviderNotFoundError:
                logger.debug("No chat provider configured, skip LLM analysis")
            except Exception:
                logger.exception("LLM analysis failed")

    def _build_render_data(self, event: AstrMessageEvent) -> tuple[str, StatusPayload]:
        """为渲染构建模板和负载数据。"""
        html = self.template_path.read_text(encoding="utf-8-sig")
        banner_uri = ""
        if self.banner_paths and isinstance(self.banner_paths, list):
            chosen_path_str = random.choice(self.banner_paths)
            logger.info(f"尝试使用自定义 Banner: {chosen_path_str}")
            banner_uri = get_image_data_uri(chosen_path_str, self.base_dir, self.plugin_data_dir, is_user_path=True)

        if not banner_uri:
            if self.default_banner_dir.exists():
                default_banners = [p for p in self.default_banner_dir.iterdir() if p.is_file()]
                if default_banners:
                    chosen_default_path = random.choice(default_banners)
                    logger.info(f"使用默认 Banner: {chosen_default_path.relative_to(self.base_dir)}")
                    banner_uri = get_image_data_uri(chosen_default_path.relative_to(self.base_dir), self.base_dir, self.plugin_data_dir)

        char_files = [p for p in self.character_dir.iterdir() if p.is_file()] if self.character_dir.exists() else []
        if char_files:
            character_uri = get_image_data_uri(random.choice(char_files).relative_to(self.base_dir), self.base_dir, self.plugin_data_dir)
        else:
            character_uri = ""

        css = self.css_path.read_text(encoding="utf-8-sig")
        css = css.replace("${topBannerImage}", banner_uri or "")
        css = css.replace("${characterImage}", character_uri or "")
        css = inline_fonts_in_css(css, self.base_dir)

        inlined_css = f"<style>{css}</style>"

        upload_kbs, download_kbs = self.data_source.get_net_speed_kbs()
        plugin_count_str = str(self.data_source.get_plugin_counts())

        payload = StatusPayload(
            css_style=inlined_css,
            bot_name=self.bot_name,
            metrics=self.data_source.get_metrics(),
            cpu_name=self.data_source.get_cpu_name(),
            os_name=self.data_source.get_os_name(),
            project_version=self.data_source.get_project_version(event),
            plugin_count=plugin_count_str,
            upload_speed=f"{upload_kbs:.1f}",
            download_speed=f"{download_kbs:.1f}",
            dashboard_name="AstrBot",
            uptime=self.data_source.get_uptime_text(),
        )
        return html, payload
