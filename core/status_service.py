from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import mcp.types

from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context, StarTools
from astrbot.core.exceptions import ProviderNotFoundError
from astrbot.core.message.message_event_result import MessageChain

from .config_manager import ConfigManager
from .constants import LLM_TIMEOUT
from .html_render import HtmlRender
from .logger import logger


class StatusService:
    """负责命令/tool 路由、消息发送和 LLM 分析分支。"""

    def __init__(
        self,
        *,
        config_manager: ConfigManager,
        context: Context,
        html_renderer: HtmlRender,
    ) -> None:
        self.context = context
        self.config_manager = config_manager
        self.html_renderer = html_renderer

    async def get_status_tool_handler(
        self, event: AstrMessageEvent
    ) -> mcp.types.CallToolResult:
        """LLM tool handler：发送状态图，并返回可供模型读取的文本摘要。"""
        try:
            image_url = await self.html_renderer.render_status_image(event)
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

        try:
            return mcp.types.CallToolResult(
                content=[
                    mcp.types.TextContent(
                        type="text",
                        text=await self.html_renderer.build_status_text(event),
                    )
                ]
            )
        except Exception:
            logger.exception("获取系统状态信息失败")
            return mcp.types.CallToolResult(
                content=[
                    mcp.types.TextContent(type="text", text="获取系统状态信息失败。")
                ]
            )

    async def show_status(self, event: AstrMessageEvent) -> AsyncIterator[Any]:
        """处理 /status 命令，先返回状态图，再按配置追加 LLM 分析。"""
        try:
            image_url = await self.html_renderer.render_status_image(event)
        except Exception:
            logger.exception("状态图片渲染失败")
            yield event.plain_result("状态图片渲染失败，请稍后再试。")
            return

        yield event.image_result(image_url)

        async for result in self.analyze_status_image(event, image_url):
            yield result

    async def analyze_status_image(
        self,
        event: AstrMessageEvent,
        image_url: str,
    ) -> AsyncIterator[Any]:
        llm_config = self.config_manager.llm_analysis
        if not llm_config.enabled:
            return

        try:
            umo = event.unified_msg_origin
            v_pid = await self.resolve_provider(
                llm_config.vision_provider_id,
                umo,
                prefer_vision=True,
            )
            if not v_pid:
                logger.warning("未配置视觉模型，跳过 LLM 分析")
                yield event.plain_result(
                    "系统状态图片已生成，但未配置视觉模型，无法进行AI分析。"
                )
                return
            logger.info(f"识图模型: {v_pid}")

            async with asyncio.timeout(LLM_TIMEOUT):
                vision_resp = await self.context.llm_generate(
                    chat_provider_id=v_pid,
                    prompt=llm_config.vision_prompt,
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
            logger.info(f"识图结果: {description[:80]}...")

            c_pid = await self.resolve_provider(
                llm_config.comment_provider_id,
                umo,
            )
            if not c_pid:
                logger.warning("未配置转述模型，直接返回识图结果")
                yield event.plain_result(description)
                return
            logger.info(f"转述模型: {c_pid}")

            final_prompt = llm_config.comment_prompt.replace(
                "{description}",
                description,
            )
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

    async def resolve_provider(
        self, config_pid: str, umo: str, prefer_vision: bool = False
    ) -> str:
        """解析 provider ID：配置 > 全局视觉模型 > 当前会话模型。"""
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
            except (KeyError, AttributeError, TypeError) as e:
                logger.warning(f"获取全局图片描述模型配置异常: {e}")
        try:
            pid = await self.context.get_current_chat_provider_id(umo=umo)
            if pid:
                return str(pid).strip()
        except (ProviderNotFoundError, KeyError, AttributeError, TypeError) as e:
            logger.warning(f"获取当前会话模型失败: {e}")
        return ""
