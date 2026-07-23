from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from tests.support import create_core_package, load_core_module

PACKAGE_NAME = "status_core_state_store_tests"

create_core_package(PACKAGE_NAME)
state_store_module = load_core_module(PACKAGE_NAME, "state_store")

JsonStateStore = state_store_module.JsonStateStore


def test_state_store_instances_for_same_file_share_lock(tmp_path: Path) -> None:
    first = JsonStateStore(tmp_path, "status_state.json")
    second = JsonStateStore(tmp_path, "status_state.json")

    assert first._lock is second._lock


def test_state_store_preserves_existing_namespaces(tmp_path: Path) -> None:
    first = JsonStateStore(tmp_path, "status_state.json")
    second = JsonStateStore(tmp_path, "status_state.json")

    first.save_namespace("traffic_monitor", {"month": "2026-07"})
    second.save_namespace("future_feature", {"enabled": True})

    saved = json.loads((tmp_path / "status_state.json").read_text("utf-8"))

    assert saved["traffic_monitor"] == {"month": "2026-07"}
    assert saved["future_feature"] == {"enabled": True}


def test_state_store_concurrent_writes_preserve_all_namespaces(tmp_path: Path) -> None:
    namespace_count = 16
    barrier = Barrier(namespace_count)

    def save(index: int) -> None:
        store = JsonStateStore(tmp_path, "status_state.json")
        # 所有线程在栅栏处对齐，尽量制造同时写入的竞争窗口。
        barrier.wait()
        store.save_namespace(f"feature_{index}", {"index": index})

    with ThreadPoolExecutor(max_workers=namespace_count) as executor:
        for future in [executor.submit(save, i) for i in range(namespace_count)]:
            future.result()

    saved = json.loads((tmp_path / "status_state.json").read_text("utf-8"))

    for index in range(namespace_count):
        assert saved[f"feature_{index}"] == {"index": index}
