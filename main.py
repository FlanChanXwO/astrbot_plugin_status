from __future__ import annotations

import asyncio
import random
from dataclasses import asdict
from pathlib import Path

import mcp.types

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, StarTools
from astrbot.core.exceptions import ProviderNotFoundError
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.provider.register import llm_tools

from .data_source import SystemDataSource
from .models import StatusPayload
from .utils import get_image_data_uri, inline_fonts_in_css

# 默认超时时间（秒）
DEFAULT_TIMEOUT = 30
LLM_TIMEOUT = 60


class StatusPlugin(Star):
    """
    一个用于渲染系统状态卡的插件。
    """

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.base_dir = Path(__file__).parent
        self.config = config
        self.plugin_data_dir = StarTools.get_data_dir(self.name)
        self.template_path = self.base_dir / "templates" / "main.html"
        self.css_path = self.base_dir / "templates" / "res" / "css" / "style.css"
        self.character_dir = self.base_dir / "templates" / "res" / "image" / "character"
        self.default_banner_dir = (
            self.base_dir / "templates" / "res" / "image" / "banner"
        )
        self.render_options = {"full_page": True, "type": "png", "scale": "device"}
        self.data_source = SystemDataSource(context, self.base_dir)

        # 配置值类型校验
        bot_name = config.get("bot_name")
        self.bot_name = bot_name if isinstance(bot_name, str) else "AstrBot"

        banner_image = config.get("banner_image")
        # 校验 banner_image 是否为字符串列表
        if isinstance(banner_image, list) and all(
            isinstance(x, str) for x in banner_image
        ):
            self.banner_paths = banner_image
        else:
            self.banner_paths = []

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

    async def _get_status_tool_handler(
        self, event: AstrMessageEvent
    ) -> mcp.types.CallToolResult:
        """LLM tool handler: 返回系统状态指标文本信息，同时发送图片给用户。"""
        from datetime import datetime

        # 先尝试渲染图片发送给用户
        image_url = None
        try:
            html_content, payload = await self._build_render_data(event)
            payload_dict = asdict(payload)
            image_url = await self.html_render(
                html_content,
                payload_dict,
                return_url=True,
                options=self.render_options,
            )
            # 发送图片给用户
            try:
                await StarTools.send_message(
                    session=event.session,
                    message_chain=MessageChain().url_image(image_url),
                )
                logger.info("Status image sent to user via StarTools.send_message()")
            except Exception as e:
                logger.warning(
                    f"Failed to send image via StarTools.send_message() to session {event.session}: {e}"
                )
        except Exception as e:
            logger.warning(f"Failed to render status image: {e}")

        # 构建并返回文本指标给 LLM
        try:
            metrics = self.data_source.get_metrics()
            cpu_name = await self.data_source.get_cpu_name()
            os_name = self.data_source.get_os_name()
            project_version = self.data_source.get_project_version(event)
            plugin_count = await self.data_source.get_plugin_counts()
            upload_kbs, download_kbs = self.data_source.get_net_speed_kbs()
            uptime = self.data_source.get_uptime_text()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            metrics_map = {m.label: m.value for m in metrics}

            status_text = f"""\
系统状态信息
================
机器人名称: {self.bot_name}
当前时间: {current_time}
框架版本: {project_version}
运行时间: {uptime}

系统信息
--------
操作系统: {os_name}
CPU: {cpu_name}

资源使用
--------
CPU: {metrics_map.get("CPU", "N/A")}
内存: {metrics_map.get("RAM", "N/A")}
交换: {metrics_map.get("SWAP", "N/A")}
磁盘: {metrics_map.get("DISK", "N/A")}
负载: {metrics_map.get("LOAD", "N/A")}

网络与插件
----------
网络速度: ↑{upload_kbs:.1f} KB/s ↓{download_kbs:.1f} KB/s
已加载插件: {plugin_count} 个"""

            return mcp.types.CallToolResult(
                content=[mcp.types.TextContent(type="text", text=status_text)]
            )
        except Exception:
            logger.exception("获取系统状态信息失败")
            return mcp.types.CallToolResult(
                content=[
                    mcp.types.TextContent(type="text", text="获取系统状态信息失败。")
                ]
            )

    @filter.command("status", alias={"状态"})
    async def show_status(self, event: AstrMessageEvent):
        """返回状态图片"""
        try:
            html_content, payload = await self._build_render_data(event)
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
                umo = event.unified_msg_origin
                vision_pid = str(
                    self.config.get("vision_provider_id", "") or ""
                ).strip()
                comment_pid = str(
                    self.config.get("comment_provider_id", "") or ""
                ).strip()
                vision_prompt = self.config.get(
                    "vision_prompt",
                    "把图片中各种指标用文字描述出来",
                )
                comment_prompt = self.config.get(
                    "comment_prompt",
                    "根据以下系统状态描述，用简洁友好的语气总结当前服务器状况，重点关注异常项。\n\n系统状态描述：{description}",
                )

                # 第一步：视觉模型识图
                v_pid = await self._resolve_provider(
                    vision_pid, umo, prefer_vision=True
                )
                if not v_pid:
                    logger.warning("未配置视觉模型，跳过 LLM 分析")
                    yield event.plain_result(
                        "系统状态图片已生成，但未配置视觉模型，无法进行AI分析。"
                    )
                    return
                logger.info(f"[Status] 识图模型: {v_pid}")

                async with asyncio.timeout(LLM_TIMEOUT):
                    vision_resp = await self.context.llm_generate(
                        chat_provider_id=v_pid,
                        prompt=vision_prompt,
                        image_urls=[image_url],
                    )
                description = (
                    (vision_resp.completion_text or "").strip() if vision_resp else ""
                )
                if not description:
                    logger.warning("视觉模型返回空结果")
                    yield event.plain_result(
                        "系统状态图片已生成，但视觉模型未返回分析结果。"
                    )
                    return
                logger.info(f"[Status] 识图结果: {description[:80]}...")

                # 第二步：文本模型转述
                c_pid = await self._resolve_provider(comment_pid, umo)
                if not c_pid:
                    logger.warning("未配置转述模型，直接返回识图结果")
                    yield event.plain_result(description)
                    return
                logger.info(f"[Status] 转述模型: {c_pid}")

                final_prompt = comment_prompt.replace("{description}", description)
                async with asyncio.timeout(LLM_TIMEOUT):
                    comment_resp = await self.context.llm_generate(
                        chat_provider_id=c_pid,
                        prompt=final_prompt,
                    )
                if comment_resp and comment_resp.completion_text:
                    yield event.plain_result(comment_resp.completion_text)
                else:
                    logger.warning("转述模型返回空结果，回退到识图结果")
                    yield event.plain_result(description)
            except asyncio.TimeoutError:
                logger.warning("LLM analysis timed out")
                yield event.plain_result("大模型识别分析超时，请尝试更换模型或者重试。")
            except ProviderNotFoundError:
                logger.debug("No chat provider configured, skip LLM analysis")
            except Exception:
                logger.exception("LLM analysis failed")

    async def _resolve_provider(
        self, config_pid: str, umo: str, prefer_vision: bool = False
    ) -> str:
        """解析 provider ID。优先级：配置 > 框架全局视觉模型 > 当前会话模型。"""
        if config_pid:
            return config_pid
        if prefer_vision:
            try:
                cfg = self.context.get_config()
                vlm_id = str(
                    (cfg.get("provider_settings") or {}).get(
                        "default_image_caption_provider_id", ""
                    )
                    or ""
                ).strip()
                if vlm_id:
                    return vlm_id
            except Exception:
                pass
        try:
            pid = await self.context.get_current_chat_provider_id(umo=umo)
            if pid:
                return str(pid).strip()
        except Exception:
            pass
        return ""

    async def _build_render_data(
        self, event: AstrMessageEvent
    ) -> tuple[str, StatusPayload]:
        """为渲染构建模板和负载数据。"""
        html = self.template_path.read_text(encoding="utf-8-sig")
        banner_uri = ""
        if self.banner_paths and isinstance(self.banner_paths, list):
            chosen_path_str = random.choice(self.banner_paths)
            logger.info(f"尝试使用自定义 Banner: {chosen_path_str}")
            banner_uri = get_image_data_uri(
                chosen_path_str, self.base_dir, self.plugin_data_dir, is_user_path=True
            )

        if not banner_uri:
            if self.default_banner_dir.exists():
                default_banners = [
                    p for p in self.default_banner_dir.iterdir() if p.is_file()
                ]
                if default_banners:
                    chosen_default_path = random.choice(default_banners)
                    logger.info(
                        f"使用默认 Banner: {chosen_default_path.relative_to(self.base_dir)}"
                    )
                    banner_uri = get_image_data_uri(
                        chosen_default_path.relative_to(self.base_dir),
                        self.base_dir,
                        self.plugin_data_dir,
                    )

        char_files = (
            [p for p in self.character_dir.iterdir() if p.is_file()]
            if self.character_dir.exists()
            else []
        )
        if char_files:
            character_uri = get_image_data_uri(
                random.choice(char_files).relative_to(self.base_dir),
                self.base_dir,
                self.plugin_data_dir,
            )
        else:
            character_uri = ""

        css = self.css_path.read_text(encoding="utf-8-sig")
        css = css.replace("${topBannerImage}", banner_uri or "")
        css = css.replace("${characterImage}", character_uri or "")
        css = inline_fonts_in_css(css, self.base_dir)

        inlined_css = f"<style>{css}</style>"

        upload_kbs, download_kbs = self.data_source.get_net_speed_kbs()
        plugin_count_str = str(await self.data_source.get_plugin_counts())

        payload = StatusPayload(
            css_style=inlined_css,
            bot_name=self.bot_name,
            metrics=self.data_source.get_metrics(),
            cpu_name=await self.data_source.get_cpu_name(),
            os_name=self.data_source.get_os_name(),
            project_version=self.data_source.get_project_version(event),
            plugin_count=plugin_count_str,
            upload_speed=f"{upload_kbs:.1f}",
            download_speed=f"{download_kbs:.1f}",
            dashboard_name="AstrBot",
            uptime=self.data_source.get_uptime_text(),
        )
        return html, payload
