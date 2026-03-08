from __future__ import annotations

import base64
import logging
from pathlib import Path

from astrbot.core.utils.io import download_image_by_url

logger = logging.getLogger(__name__)


def inline_fonts_in_css(css: str, base_dir: Path) -> str:
    """Replace relative font url() in CSS with base64 data URIs when font files exist."""
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
    path = Path(image_path)
    if not path.is_absolute():
        base = plugin_data_dir if is_user_path else base_dir
        path = base / path

    if not path.exists() or not path.is_file():
        logger.warning(f"图片文件不存在: {path}")
        return ""
    try:
        suffix = path.suffix.lower().lstrip(".") or "png"
        mime = "jpeg" if suffix in {"jpg", "jpeg"} else "png"
        encoded_data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:image/{mime};base64,{encoded_data}"
    except Exception as e:
        logger.error(f"读取或编码图片失败: {path}, 错误: {e}")
        return ""


async def image_url_to_base64(image_url: str) -> str | None:
    """Convert image URL (http or local path) to base64 string."""
    try:
        if image_url.startswith("http"):
            path = await download_image_by_url(image_url)
        else:
            path = image_url
        data = Path(path).read_bytes()
        return base64.b64encode(data).decode("ascii")
    except Exception as e:
        logger.warning("Failed to convert image to base64: %s", e)
        return None
