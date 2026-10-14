from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone(timedelta(hours=8)))


def load_module():
    path = ROOT / "scripts" / "youmind-added-time.py"
    spec = importlib.util.spec_from_file_location("youmind_added_time_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_decodes_uuidv7_source_id_to_beijing_time() -> None:
    module = load_module()
    result = module.check_sources(
        {
            "sources": [
                {
                    "source_id": "01a09fe9-c37b-71bd-baf9-e87514ea4631",
                    "published_at": "2026-09-13T20:16",
                }
            ]
        },
        NOW,
    )

    item = result["sources"][0]
    assert item["added_at"] == "2026-09-14T20:34:52+08:00"
    assert item["verified"] is True
    assert result["board"]["name"] == "灵感收集"


def test_orders_sources_newest_first() -> None:
    module = load_module()
    result = module.check_sources(
        {
            "sources": [
                {"source_id": "01a03c16-7b89-7372-8c99-a600e926dc54"},
                {"source_id": "01a07a16-89fb-7203-9520-7b337777fbe8"},
                {"source_id": "01a03c1a-58b1-750e-9433-360c9d7d9465"},
            ]
        },
        NOW,
    )

    assert [item["source_id"][:8] for item in result["sources"]] == [
        "01a07a16",
        "01a03c1a",
        "01a03c16",
    ]
    assert result["sources"][0]["added_at"] == "2026-09-07T12:18:12+08:00"
    assert result["verified"] is True


def test_rejects_non_v7_id_and_added_before_published() -> None:
    module = load_module()
    result = module.check_sources(
        {
            "sources": [
                {"source_id": "550e8400-e29b-41d4-a716-446655440000"},
                {
                    "source_id": "01a03c16-7b89-7372-8c99-a600e926dc54",
                    "published_at": "2026-09-01T00:00:00+08:00",
                },
            ]
        },
        NOW,
    )

    assert result["verified"] is False
    problems = "；".join(
        problem for item in result["sources"] for problem in item["problems"]
    )
    assert "不是 UUIDv7" in problems
    assert "早于原帖发布时间" in problems


def test_orders_sources_within_the_same_second_by_milliseconds() -> None:
    module = load_module()
    older = "01a09fe9-c37b-71bd-baf9-e87514ea4631"
    newer = "01a09fe9-c37c-71bd-baf9-e87514ea4631"
    result = module.check_sources(
        {"sources": [{"source_id": older}, {"source_id": newer}]}, NOW
    )

    assert result["sources"][0]["added_at"] == result["sources"][1]["added_at"]
    assert [item["source_id"] for item in result["sources"]] == [newer, older]
