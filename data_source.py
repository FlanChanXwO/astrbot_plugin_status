from __future__ import annotations

import datetime as dt
import platform
import shutil
import time
from pathlib import Path

import psutil

from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context

from .models import Metric


class SystemDataSource:
    """
    系统数据源，用于获取系统状态信息
    """

    def __init__(self, context: Context, base_dir: Path):
        self.context = context
        self.base_dir = base_dir
        self._last_net_bytes_sent = 0
        self._last_net_bytes_recv = 0
        self._last_net_sample_ts = 0.0
        self._process_start = dt.datetime.now()

    def _truncate_text(self, text: str, max_length: int = 40) -> str:
        """如果文本超过最大长度，则截断并添加省略号"""
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text

    def get_metrics(self) -> list[Metric]:
        """
        获取所有系统指标
        :return: 指标列表
        """
        cpu_pct = self._cpu_percent()
        mem_used_gb, mem_total_gb, mem_pct = self._memory_usage()
        swap_used_gb, swap_total_gb, swap_pct = self._swap_usage()
        disk_used_gb, disk_total_gb, disk_pct = self._disk_usage()
        load_pct = self._load_percent(cpu_pct)

        return [
            Metric(
                icon_class="icon-cpu",
                label="CPU",
                value=self._cpu_display(cpu_pct),
                offset=self._offset(cpu_pct),
            ),
            Metric(
                icon_class="icon-ram",
                label="RAM",
                value=f"{mem_used_gb:.2f} / {mem_total_gb:.2f} GB",
                offset=self._offset(mem_pct),
            ),
            Metric(
                icon_class="icon-swap",
                label="SWAP",
                value=f"{swap_used_gb:.2f} / {swap_total_gb:.2f} GB",
                offset=self._offset(swap_pct),
            ),
            Metric(
                icon_class="icon-disk",
                label="DISK",
                value=f"{disk_used_gb:.2f} / {disk_total_gb:.2f} GB",
                offset=self._offset(disk_pct),
            ),
            Metric(
                icon_class="icon-load",
                label="PAYLOAD",
                value=f"{load_pct:.1f}% / 100%",
                offset=self._offset(load_pct),
            ),
        ]

    def get_cpu_name(self) -> str:
        """获取CPU名称，并截断过长的部分"""
        cpu_name = self._get_cpu_name_linux()
        return self._truncate_text(cpu_name)

    def _get_cpu_name_linux(self) -> str:
        """在Linux上获取CPU名称"""
        try:
            # 尝试从/proc/cpuinfo读取
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
                    # ARM处理器可能用不同的字段
                    if line.startswith("Hardware"):
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass

        # 尝试用psutil
        if psutil is not None:
            try:
                freq = psutil.cpu_freq()
                cores = psutil.cpu_count() or 1
                if freq and freq.current:
                    ghz = freq.current / 1000.0
                    return f"{cores} Core @ {ghz:.2f}GHz"
            except Exception:
                pass

        # 回退到platform
        cpu_name = platform.processor()
        if cpu_name:
            return cpu_name

        return "Unknown CPU"

    def get_os_name(self) -> str:
        """获取操作系统名称，并截断过长的部分"""
        os_name = f"{platform.system()} {platform.release()}"
        return self._truncate_text(os_name)

    def get_project_version(self, event: AstrMessageEvent) -> str:
        """获取AstrBot项目版本"""
        try:
            # 尝试从astrbot获取版本
            from astrbot import __version__ as astr_ver
            if astr_ver:
                return f"AstrBot v{astr_ver}"
        except ImportError:
            pass

        try:
            from astrbot.cli import __version__ as cli_ver
            if cli_ver:
                return f"AstrBot v{cli_ver}"
        except ImportError:
            pass

        try:
            from astrbot.core import __version__ as core_ver
            if core_ver:
                return f"AstrBot v{core_ver}"
        except ImportError:
            pass

        return "AstrBot"

    def get_plugin_counts(self) -> int:
        """获取插件的数量"""
        getter = getattr(self.context, "get_all_stars", None)
        if not callable(getter):
            return 0
        try:
            stars = getter()
            if not isinstance(stars, list):
                return 0
            return len(stars)
        except Exception:
            return 0

    def get_net_speed_kbs(self) -> tuple[float, float]:
        """获取上传和下载速度 (KB/s)"""
        if psutil is None:
            return 0.0, 0.0

        now = time.monotonic()
        try:
            io = psutil.net_io_counters()
            if self._last_net_sample_ts <= 0:
                self._last_net_sample_ts = now
                self._last_net_bytes_sent = int(io.bytes_sent)
                self._last_net_bytes_recv = int(io.bytes_recv)
                return 0.0, 0.0

            elapsed = max(0.001, now - self._last_net_sample_ts)
            up = max(0, int(io.bytes_sent) - self._last_net_bytes_sent)
            down = max(0, int(io.bytes_recv) - self._last_net_bytes_recv)

            self._last_net_sample_ts = now
            self._last_net_bytes_sent = int(io.bytes_sent)
            self._last_net_bytes_recv = int(io.bytes_recv)

            return up / elapsed / 1024.0, down / elapsed / 1024.0
        except Exception:
            return 0.0, 0.0

    def get_uptime_text(self) -> str:
        """获取运行时间文本"""
        delta = dt.datetime.now() - self._process_start
        total = int(delta.total_seconds())
        days, rem = divmod(total, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)
        if days > 0:
            return f"{days}天{hours}小时{minutes}分"
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _cpu_display(self, cpu_pct: float) -> str:
        if psutil is None:
            return f"{cpu_pct:.1f}%"
        try:
            freq = psutil.cpu_freq()
            cores = psutil.cpu_count() or 1
            mhz = 0.0
            if freq is not None:
                mhz = float(freq.current or freq.max or 0.0)
            ghz = mhz / 1000.0 if mhz > 0 else 0.0
            if ghz > 0:
                return f"{cpu_pct:.1f}% - {ghz:.2f}GHz [{cores} Core]"
            return f"{cpu_pct:.1f}% [{cores} 核]"
        except Exception:
            return f"{cpu_pct:.1f}%"

    def _cpu_percent(self) -> float:
        if psutil is None:
            return 0.0
        try:
            return float(psutil.cpu_percent(interval=None))
        except Exception:
            return 0.0

    def _memory_usage(self) -> tuple[float, float, float]:
        if psutil is None:
            return 0.0, 0.0, 0.0
        try:
            vm = psutil.virtual_memory()
            used = (vm.total - vm.available) / (1024 ** 3)
            total = vm.total / (1024 ** 3)
            return used, total, float(vm.percent)
        except Exception:
            return 0.0, 0.0, 0.0

    def _swap_usage(self) -> tuple[float, float, float]:
        if psutil is None:
            return 0.0, 0.0, 0.0
        try:
            sm = psutil.swap_memory()
            used = sm.used / (1024 ** 3)
            total = sm.total / (1024 ** 3)
            pct = float(sm.percent if sm.total else 0.0)
            return used, total, pct
        except Exception:
            return 0.0, 0.0, 0.0

    def _disk_usage(self) -> tuple[float, float, float]:
        try:
            du = shutil.disk_usage(str(Path.cwd()))
            used = du.used / (1024 ** 3)
            total = du.total / (1024 ** 3)
            pct = (used / total) * 100 if total else 0.0
            return used, total, pct
        except Exception:
            return 0.0, 0.0, 0.0

    def _load_percent(self, cpu_pct: float) -> float:
        if psutil is None:
            return cpu_pct
        try:
            la1, _, _ = psutil.getloadavg()
            cpu_count = psutil.cpu_count() or 1
            return min(100.0, max(cpu_pct, (la1 / cpu_count) * 100))
        except Exception:
            return cpu_pct

    def _offset(self, percent: float) -> float:
        p = min(100.0, max(0.0, percent))
        return 339.29 * (1.0 - (p / 100.0))
