from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests
from jinja2 import Template
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
T2I_ENDPOINT = "http://localhost:8999/text2img/generate"


def _metric(
    icon_class: str, label: str, value: str, offset: float
) -> dict[str, object]:
    return {
        "icon_class": icon_class,
        "label": label,
        "value": value,
        "offset": offset,
    }


def _render_payload() -> tuple[str, dict[str, object]]:
    html = (ROOT / "templates/main.html").read_text(encoding="utf-8-sig")
    css = (ROOT / "templates/res/css/style.css").read_text(encoding="utf-8-sig")
    css = css.replace("${topBannerImage}", "")
    css = css.replace("${characterImage}", "")

    payload: dict[str, object] = {
        "css_style": f"<style>{css}</style>",
        "bot_name": "AstrBot",
        "metrics": [
            _metric("icon-cpu", "CPU", "12.3% - 3.20GHz [8 Core]", 297.55),
            _metric("icon-ram", "RAM", "4.25 / 16.00 GB", 249.11),
            _metric("icon-swap", "SWAP", "0.00 / 2.00 GB", 339.29),
            _metric("icon-disk", "DISK", "120.00 / 512.00 GB", 259.79),
            _metric("icon-load", "LOAD", "22.0% / 100%", 264.65),
        ],
        "cpu_name": "Apple M1 Pro",
        "os_name": "Darwin 25.0.0",
        "project_version": "AstrBot v4.0.0",
        "plugin_count": "12",
        "upload_speed": "1.2",
        "download_speed": "3.4",
        "dashboard_name": "AstrBot",
        "uptime": "00:12:34",
    }
    return html, payload


def test_background_paws_stay_inside_card() -> None:
    html = (ROOT / "templates/main.html").read_text(encoding="utf-8-sig")
    card_start = html.index('<div class="card">')
    card_end = html.index("</div>\n\n</body>")

    for class_name in (
        "bg-tiny-paw",
        "bg-small-paw",
        "bg-medium-paw",
        "bg-big-paw",
    ):
        paw_index = html.index(class_name)
        assert card_start < paw_index < card_end


def test_template_viewport_matches_card_width() -> None:
    html = (ROOT / "templates/main.html").read_text(encoding="utf-8-sig")

    assert 'content="width=500' in html
    assert "height=1000" not in html


def test_rendered_template_contains_paw_decorations() -> None:
    html, payload = _render_payload()
    rendered = Template(html).render(
        **{
            key: [
                SimpleNamespace(**item) if isinstance(item, dict) else item
                for item in value
            ]
            if key == "metrics"
            else value
            for key, value in payload.items()
        }
    )

    assert 'class="card"' in rendered
    assert rendered.count("bg-") >= 4


def test_bottom_paw_decorations_remain_visible_inside_card() -> None:
    css = (ROOT / "templates/res/css/style.css").read_text(encoding="utf-8-sig")

    for class_name in ("bg-small-paw", "bg-big-paw"):
        rule = re.search(
            rf"^\s*\.{class_name}\s*\{{(?P<body>[^}}]+)\}}",
            css,
            re.MULTILINE,
        )
        assert rule is not None

        bottom = re.search(r"bottom:\s*(-?\d+)px", rule["body"])
        height = re.search(r"height:\s*(\d+)px", rule["body"])
        assert bottom is not None
        assert height is not None
        assert int(bottom.group(1)) > -int(height.group(1))


def test_t2i_render_has_no_large_white_bottom_gap() -> None:
    html, payload = _render_payload()
    post_data = {
        "tmpl": html,
        "tmpldata": payload,
        "json": True,
        "options": {"full_page": True, "type": "png", "scale": "device"},
    }

    try:
        response = requests.post(T2I_ENDPOINT, json=post_data, timeout=15)
    except requests.RequestException as exc:
        pytest.skip(f"T2I service is unavailable: {exc}")

    if response.status_code >= 500:
        pytest.skip(f"T2I service is unavailable: HTTP {response.status_code}")
    response.raise_for_status()

    image_id = response.json()["data"]["id"]
    image_url = f"http://localhost:8999/text2img/{image_id}"
    image_response = requests.get(image_url, timeout=15)
    image_response.raise_for_status()

    output_dir = ROOT / "tests" / "output"
    output_dir.mkdir(exist_ok=True)
    image_path = output_dir / "status_t2i_regression.jpg"
    image_path.write_bytes(image_response.content)

    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    bottom_band = image.crop((0, max(0, height - 160), width, height))
    pixels = list(bottom_band.get_flattened_data())
    near_white = sum(
        1 for red, green, blue in pixels if red > 245 and green > 245 and blue > 245
    )
    near_white_ratio = near_white / len(pixels)

    assert width == 500
    assert near_white_ratio < 0.2
