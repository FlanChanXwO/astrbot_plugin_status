from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def install_astrbot_stubs(*, include_event: bool = False) -> None:
    """安装测试所需的 AstrBot 模块桩，避免导入真实运行时。"""
    astrbot_module = types.ModuleType("astrbot")
    astrbot_api_module = types.ModuleType("astrbot.api")
    astrbot_api_module.logger = SimpleNamespace(
        debug=lambda *args, **kwargs: None,
        info=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
        exception=lambda *args, **kwargs: None,
        critical=lambda *args, **kwargs: None,
    )
    sys.modules.setdefault("astrbot", astrbot_module)
    sys.modules.setdefault("astrbot.api", astrbot_api_module)
    astrbot_core_module = types.ModuleType("astrbot.core")
    astrbot_core_utils_module = types.ModuleType("astrbot.core.utils")
    astrbot_core_utils_io_module = types.ModuleType("astrbot.core.utils.io")
    astrbot_core_utils_io_module.download_image_by_url = lambda url: url
    sys.modules.setdefault("astrbot.core", astrbot_core_module)
    sys.modules.setdefault("astrbot.core.utils", astrbot_core_utils_module)
    sys.modules.setdefault("astrbot.core.utils.io", astrbot_core_utils_io_module)

    if include_event:
        astrbot_event_module = types.ModuleType("astrbot.api.event")
        astrbot_star_module = types.ModuleType("astrbot.api.star")
        astrbot_event_module.AstrMessageEvent = object
        astrbot_star_module.Context = object
        sys.modules.setdefault("astrbot.api.event", astrbot_event_module)
        sys.modules.setdefault("astrbot.api.star", astrbot_star_module)


def install_psutil_stub() -> types.ModuleType:
    """安装 SystemDataSource 测试用 psutil 桩。"""
    psutil_module = types.ModuleType("psutil")
    psutil_module.Process = lambda _pid: SimpleNamespace(create_time=lambda: 0.0)
    psutil_module.cpu_freq = lambda: None
    psutil_module.cpu_count = lambda logical=True: 1
    psutil_module.cpu_percent = lambda interval=None: 0.0
    psutil_module.virtual_memory = lambda: SimpleNamespace(
        total=0,
        available=0,
        percent=0.0,
    )
    psutil_module.swap_memory = lambda: SimpleNamespace(
        total=0,
        used=0,
        percent=0.0,
    )
    psutil_module.net_io_counters = lambda: SimpleNamespace(
        bytes_sent=0,
        bytes_recv=0,
    )
    psutil_module.getloadavg = lambda: (0.0, 0.0, 0.0)
    sys.modules.setdefault("psutil", psutil_module)
    return psutil_module


def create_core_package(package_name: str) -> types.ModuleType:
    """创建指向 core 目录的临时包，支持相对导入。"""
    package = types.ModuleType(package_name)
    package.__path__ = [str(ROOT / "core")]
    sys.modules[package_name] = package
    return package


def load_core_module(package_name: str, module_name: str) -> types.ModuleType:
    """按临时包名加载 core 模块。"""
    spec = importlib.util.spec_from_file_location(
        f"{package_name}.{module_name}",
        ROOT / "core" / f"{module_name}.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
