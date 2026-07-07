from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any, ClassVar

STATE_STORE_SCHEMA_VERSION = 1


class JsonStateStore:
    """插件级 JSON 状态仓库，按命名空间保存不同功能的轻量状态。"""

    _locks_by_path: ClassVar[dict[Path, RLock]] = {}
    _locks_guard: ClassVar[RLock] = RLock()

    def __init__(self, data_dir: Path, filename: str) -> None:
        self.data_dir = data_dir
        self.path = self.data_dir / filename
        self._lock = self._lock_for_path(self.path)

    @classmethod
    def _lock_for_path(cls, path: Path) -> RLock:
        key = path.resolve(strict=False)
        with cls._locks_guard:
            return cls._locks_by_path.setdefault(key, RLock())

    def load_namespace(self, name: str) -> dict[str, Any]:
        """读取某个功能命名空间；缺失时返回空状态。"""
        with self._lock:
            data = self._load()
            namespace = data.get(name)
            return namespace if isinstance(namespace, dict) else {}

    def save_namespace(
        self,
        name: str,
        state: dict[str, Any],
        *,
        reset_on_corrupt: bool = False,
    ) -> None:
        """原子写回某个功能命名空间，避免未来功能各自散落状态文件。"""
        with self._lock:
            try:
                data = self._load()
            except (json.JSONDecodeError, UnicodeDecodeError):
                if not reset_on_corrupt:
                    raise
                # 调用方已确认旧状态不可读时，允许用当前命名空间重建插件状态。
                data = {"schema_version": STATE_STORE_SCHEMA_VERSION}
            data["schema_version"] = STATE_STORE_SCHEMA_VERSION
            data[name] = state
            self._save(data)

    def _load(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return {"schema_version": STATE_STORE_SCHEMA_VERSION}
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, dict):
                return {"schema_version": STATE_STORE_SCHEMA_VERSION}
            data.setdefault("schema_version", STATE_STORE_SCHEMA_VERSION)
            return data

    def _save(self, data: dict[str, Any]) -> None:
        with self._lock:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            temp_path = self.path.with_suffix(".tmp")
            with temp_path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
                file.write("\n")
            temp_path.replace(self.path)
