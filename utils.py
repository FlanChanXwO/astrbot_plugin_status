from __future__ import annotations

import base64
import ipaddress
from pathlib import Path
from urllib.parse import urlparse

from astrbot.core.utils.io import download_image_by_url
from astrbot.api import logger

# 最大文件读取大小: 5MB
MAX_FILE_SIZE = 5 * 1024 * 1024


def _is_safe_path(path: Path, base_dir: Path) -> bool:
    """检查路径是否在允许的目录范围内，防止路径穿越攻击"""
    try:
        # 解析路径，获取绝对路径
        resolved_path = path.resolve()
        resolved_base = base_dir.resolve()
        # 确保路径在 base_dir 下
        return resolved_path.is_relative_to(resolved_base)
    except (OSError, ValueError):
        return False


def _is_safe_url(url: str) -> bool:
    """检查 URL 是否安全，防止 SSRF 攻击"""
    try:
        parsed = urlparse(url)
        # 只允许 http 和 https 协议
        if parsed.scheme not in ("http", "https"):
            return False

        # 检查主机名是否为空
        if not parsed.hostname:
            return False

        # 禁止访问内网地址
        hostname = parsed.hostname.lower()

        # 检查是否是 IP 地址
        try:
            ip = ipaddress.ip_address(hostname)
            # 禁止内网地址
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast:
                return False
        except ValueError:
            # 不是 IP 地址，是域名
            pass

        # 禁止 localhost 相关域名
        blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "::"}
        if hostname in blocked_hosts or hostname.endswith(".localhost"):
            return False

        return True
    except Exception:
        return False


def inline_fonts_in_css(css: str, base_dir: Path) -> str:
    """通过 base64 URL 替换字体相对资源路径"""
    font_dir = base_dir / "templates" / "res" / "fonts"
    if not font_dir.is_dir():
        return css
    font_files = [
        "baotu.ttf",
        "ADLaMDisplay-Regular.ttf",
        "SpicyRice-Regular.ttf",
        "DingTalk-JinBuTi.ttf",
    ]
    for filename in font_files:
        path = font_dir / filename
        if not path.is_file():
            continue
        try:
            data_uri = f"data:font/ttf;base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
        except Exception as e:
            logger.warning("Failed to inline font %s: %s", filename, e)
            continue
        old_url = f"url('../fonts/{filename}')"
        css = css.replace(old_url, f"url('{data_uri}')")
    return css


def get_image_data_uri(
    image_path: Path | str,
    base_dir: Path,
    plugin_data_dir: Path,
    is_user_path: bool = False,
) -> str:
    """将图片文件转换为 Base64 编码的 Data URI。"""
    # 默认的 1x1 像素透明 PNG 占位图
    _placeholder_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    try:
        path = Path(image_path)
        if not path.is_absolute():
            base = plugin_data_dir if is_user_path else base_dir
            path = base / path

        # 解析为绝对路径，防止路径穿越
        path = path.resolve()

        # 安全检查：确保路径在允许的目录范围内
        allowed_dirs = [base_dir.resolve(), plugin_data_dir.resolve()]
        is_allowed = any(_is_safe_path(path, allowed) for allowed in allowed_dirs)
        if not is_allowed:
            logger.warning(f"拒绝访问路径范围外的文件: {path}")
            return _placeholder_uri

        if not path.exists() or not path.is_file():
            logger.warning(f"图片文件不存在: {path}")
            return _placeholder_uri

        # 检查文件大小，防止内存压力
        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            logger.warning(f"图片文件过大 ({file_size} bytes > {MAX_FILE_SIZE}): {path}")
            return _placeholder_uri

        suffix = path.suffix.lower().lstrip(".") or "png"
        mime = "jpeg" if suffix in {"jpg", "jpeg"} else "png"
        encoded_data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:image/{mime};base64,{encoded_data}"
    except Exception as e:
        logger.error(f"读取或编码图片失败: {image_path}, 错误: {e}")
        return _placeholder_uri


async def image_url_to_base64(image_url: str) -> str | None:
    """图片URL转base64"""
    try:
        if image_url.startswith("http"):
            # SSRF 安全检查
            if not _is_safe_url(image_url):
                logger.warning(f"拒绝访问不安全的 URL: {image_url}")
                return None
            path = await download_image_by_url(image_url)
        else:
            path = image_url

        # 检查文件大小，防止内存压力
        path_obj = Path(path)
        if path_obj.exists():
            file_size = path_obj.stat().st_size
            if file_size > MAX_FILE_SIZE:
                logger.warning(f"图片文件过大 ({file_size} bytes > {MAX_FILE_SIZE}): {path}")
                return None

        # 使用异步方式读取文件，避免阻塞事件循环
        import aiofiles
        async with aiofiles.open(path, mode="rb") as f:
            data = await f.read()
        return base64.b64encode(data).decode("ascii")
    except Exception as e:
        logger.warning("Failed to convert image to base64: %s", e)
        return None
