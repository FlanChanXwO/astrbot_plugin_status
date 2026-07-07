from __future__ import annotations

import json
from pathlib import Path

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
