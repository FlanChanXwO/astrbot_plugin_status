from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "status_core_data_source_tests"

astrbot_module = types.ModuleType("astrbot")
astrbot_api_module = types.ModuleType("astrbot.api")
astrbot_event_module = types.ModuleType("astrbot.api.event")
astrbot_star_module = types.ModuleType("astrbot.api.star")
astrbot_api_module.logger = SimpleNamespace(
    debug=lambda *args, **kwargs: None,
    info=lambda *args, **kwargs: None,
    warning=lambda *args, **kwargs: None,
    error=lambda *args, **kwargs: None,
    exception=lambda *args, **kwargs: None,
    critical=lambda *args, **kwargs: None,
)
astrbot_event_module.AstrMessageEvent = object
astrbot_star_module.Context = object
sys.modules.setdefault("astrbot", astrbot_module)
sys.modules.setdefault("astrbot.api", astrbot_api_module)
sys.modules.setdefault("astrbot.api.event", astrbot_event_module)
sys.modules.setdefault("astrbot.api.star", astrbot_star_module)

psutil_module_stub = types.ModuleType("psutil")
psutil_module_stub.Process = lambda _pid: SimpleNamespace(create_time=lambda: 0.0)
psutil_module_stub.cpu_freq = lambda: None
psutil_module_stub.cpu_count = lambda logical=True: 1
psutil_module_stub.cpu_percent = lambda interval=None: 0.0
psutil_module_stub.virtual_memory = lambda: SimpleNamespace(
    total=0,
    available=0,
    percent=0.0,
)
psutil_module_stub.swap_memory = lambda: SimpleNamespace(
    total=0,
    used=0,
    percent=0.0,
)
psutil_module_stub.net_io_counters = lambda: SimpleNamespace(bytes_sent=0, bytes_recv=0)
psutil_module_stub.getloadavg = lambda: (0.0, 0.0, 0.0)
sys.modules.setdefault("psutil", psutil_module_stub)

package = types.ModuleType(PACKAGE_NAME)
package.__path__ = [str(ROOT / "core")]
sys.modules[PACKAGE_NAME] = package


def _load_module(module_name: str, file_name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE_NAME}.{module_name}",
        ROOT / "core" / file_name,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_load_module("logger", "logger.py")
_load_module("models", "models.py")
data_source_module = _load_module("data_source", "data_source.py")

SystemDataSource = data_source_module.SystemDataSource
platform_module = data_source_module.platform
psutil_module = data_source_module.psutil


def _data_source() -> SystemDataSource:
    return SystemDataSource(SimpleNamespace(), ROOT)


@pytest.mark.asyncio
async def test_macos_cpu_name_uses_system_profiler_chip_and_sysctl_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _data_source()
    values = {
        ("system_profiler", "SPHardwareDataType"): """
Hardware:

    Hardware Overview:

      Model Name: MacBook Pro
      Chip: Apple M5
""",
        ("sysctl", "-n", "hw.physicalcpu"): "10\n",
        ("sysctl", "-n", "hw.logicalcpu"): "20\n",
    }

    async def fake_run_command_stdout(*args: str) -> str:
        return values[args]

    monkeypatch.setattr(platform_module, "system", lambda: "Darwin")
    monkeypatch.setattr(source, "_run_command_stdout", fake_run_command_stdout)

    assert await source.get_cpu_name() == "Apple M5"


@pytest.mark.asyncio
async def test_macos_cpu_name_falls_back_to_brand_string_when_chip_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _data_source()
    values = {
        ("system_profiler", "SPHardwareDataType"): "Hardware:\n",
        ("sysctl", "-n", "machdep.cpu.brand_string"): "Intel Core i9\n",
        ("sysctl", "-n", "hw.physicalcpu"): "8\n",
        ("sysctl", "-n", "hw.logicalcpu"): "16\n",
    }

    async def fake_run_command_stdout(*args: str) -> str:
        return values[args]

    monkeypatch.setattr(platform_module, "system", lambda: "Darwin")
    monkeypatch.setattr(source, "_run_command_stdout", fake_run_command_stdout)

    assert await source.get_cpu_name() == "Intel Core i9"


@pytest.mark.asyncio
async def test_macos_cpu_detail_name_does_not_include_core_or_thread_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _data_source()
    values = {
        ("system_profiler", "SPHardwareDataType"): "Chip: Apple M5\n",
    }

    async def fake_run_command_stdout(*args: str) -> str:
        return values[args]

    monkeypatch.setattr(platform_module, "system", lambda: "Darwin")
    monkeypatch.setattr(source, "_run_command_stdout", fake_run_command_stdout)

    cpu_name = await source.get_cpu_name()
    assert cpu_name == "Apple M5"
    assert "Core" not in cpu_name
    assert "Thread" not in cpu_name


def test_cpu_display_uses_physical_core_and_logical_thread_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _data_source()

    monkeypatch.setattr(
        psutil_module,
        "cpu_freq",
        lambda: SimpleNamespace(current=0.0, max=0.0),
    )
    monkeypatch.setattr(
        psutil_module,
        "cpu_count",
        lambda logical=True: 20 if logical else 10,
    )

    assert source._cpu_display(12.3) == "12.3% [10 Cores / 20 Threads]"


def test_cpu_count_text_uses_english_singular_labels() -> None:
    assert SystemDataSource._format_cpu_count_text(1, 1) == "1 Core"
    assert SystemDataSource._format_cpu_count_text(0, 1) == "1 Thread"
