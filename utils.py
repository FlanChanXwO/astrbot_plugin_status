from __future__ import annotations

import base64
import ipaddress
import os
from pathlib import Path

from astrbot.api import logger
from astrbot.core.utils.io import download_image_by_url

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


def _is_safe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """检查 IP 地址是否安全（非内网、非链路本地等）"""
    # 禁止私有地址、回环地址、保留地址、多播地址、链路本地地址
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_link_local
    ):
        return False
    return True


def inline_fonts_in_css(css: str, base_dir: Path) -> str:
    """通过 base64 URL 替换字体相对资源路径

    动态扫描 fonts 目录下的字体文件，自动识别格式并内联到 CSS 中。
    支持的格式：woff2, ttf
    """
    font_dir = base_dir / "templates" / "res" / "fonts"
    if not font_dir.is_dir():
        return css

    # MIME 类型映射
    mime_types = {
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
    }

    # 扫描字体目录，按文件名排序确保一致性
    font_files = sorted(
        [f for f in font_dir.iterdir() if f.is_file() and f.suffix.lower() in mime_types]
    )

    for font_path in font_files:
        mime_type = mime_types.get(font_path.suffix.lower())
        if not mime_type:
            continue
        try:
            data_uri = f"data:{mime_type};base64,{base64.b64encode(font_path.read_bytes()).decode('ascii')}"
        except Exception as e:
            logger.warning("Failed to inline font %s: %s", font_path.name, e)
            continue
        # 替换 url('../fonts/xxx.ttf')
        old_url = f"url('../fonts/{font_path.name}')"
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
        if suffix in {"jpg", "jpeg"}:
            mime = "jpeg"
        elif suffix == "webp":
            mime = "webp"
        else:
            mime = "png"
        encoded_data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:image/{mime};base64,{encoded_data}"
    except Exception as e:
        logger.error(f"读取或编码图片失败: {image_path}, 错误: {e}")
        return _placeholder_uri


async def image_url_to_base64(
    image_url: str,
    base_dir: Path,
    plugin_data_dir: Path,
) -> str | None:
    """图片URL转base64

    支持 http/https URL 和本地路径。对于本地路径，会检查路径安全以防止路径穿越攻击。
    下载的临时文件会在使用后自动清理。
    """
    path_str = ""
    is_temp_file = False
    try:
        # 首先将输入路径标准化（resolve 会处理 .. 和 . 等路径穿越尝试）
        path_obj = Path(image_url).resolve()

        if image_url.startswith("http"):
            path_str = await download_image_by_url(image_url)
            is_temp_file = True
            # 对下载的文件也进行 resolve，确保一致性
            path_obj = Path(path_str).resolve()
        else:
            # 本地路径，需要安全检查
            # 所有路径都必须 resolve 后检查，防止路径穿越
            allowed_dirs = [base_dir.resolve(), plugin_data_dir.resolve()]
            is_allowed = any(
                _is_safe_path(path_obj, allowed) for allowed in allowed_dirs
            )
            if not is_allowed:
                logger.warning(f"拒绝访问路径范围外的文件: {path_obj}")
                return None
            path_str = str(path_obj)

        # 检查文件大小，防止内存压力
        if path_obj.exists():
            file_size = path_obj.stat().st_size
            if file_size > MAX_FILE_SIZE:
                logger.warning(
                    f"图片文件过大 ({file_size} bytes > {MAX_FILE_SIZE}): {path_obj}"
                )
                return None

        # 使用异步方式读取文件，避免阻塞事件循环
        import aiofiles

        async with aiofiles.open(path_str, mode="rb") as f:
            data = await f.read()

        result = base64.b64encode(data).decode("ascii")

        # 如果是临时文件，清理它
        if is_temp_file and path_obj.exists():
            try:
                os.remove(path_obj)
                logger.debug(f"清理临时文件: {path_obj}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {path_obj}, {e}")

        return result
    except Exception as e:
        logger.warning("Failed to convert image to base64: %s", e)
        # 发生异常时也尝试清理临时文件
        if is_temp_file and path_str:
            try:
                temp_path = Path(path_str)
                if temp_path.exists():
                    os.remove(temp_path)
            except Exception:
                pass
        return None
