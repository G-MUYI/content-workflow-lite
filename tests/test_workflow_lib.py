from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.workflow_lib import (
    atomic_publish,
    atomic_write_text,
    parse_frontmatter_document,
    resolve_versioned_path,
    update_frontmatter_text,
)


SAMPLE = """---
title: "demo"
stage: "reviewed"
tags:
  - "AI"
  - "工作流"
voice_anchors:
  - "普通句子"
  - "包含: ASCII 冒号"
target_platforms: [wechat, xiaohongshu]
---

# 正文
"""


def test_targeted_frontmatter_update_preserves_block_sequences() -> None:
    updated = update_frontmatter_text(
        SAMPLE,
        {
            "stage": "published",
            "status": "done",
            "published_platforms": ["wechat"],
            "published_date": "2026-07-27",
        },
    )
    document = parse_frontmatter_document(updated)
    assert document is not None
    assert document.data["tags"] == ["AI", "工作流"]
    assert document.data["voice_anchors"] == ["普通句子", "包含: ASCII 冒号"]
    assert document.data["target_platforms"] == ["wechat", "xiaohongshu"]
    assert document.data["stage"] == "published"
    assert document.data["published_platforms"] == ["wechat"]
    assert "# 正文" in document.body


def test_targeted_frontmatter_update_keeps_valid_yaml() -> None:
    updated = update_frontmatter_text(SAMPLE, {"updated": "2026-07-27"})
    block = updated.split("---", 2)[1]
    parsed = yaml.safe_load(block)
    assert parsed["updated"] == "2026-07-27"


def test_resolve_versioned_path_never_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "文章.md"
    target.write_text("v1", encoding="utf-8")
    (tmp_path / "文章_v2.md").write_text("v2", encoding="utf-8")
    assert resolve_versioned_path(target).name == "文章_v3.md"


def test_atomic_publish_preserves_source_when_destination_exists(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    destination = tmp_path / "published.md"
    source.write_text("original", encoding="utf-8")
    destination.write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError):
        atomic_publish(source, destination, "new")

    assert source.read_text(encoding="utf-8") == "original"
    assert destination.read_text(encoding="utf-8") == "existing"


def test_atomic_publish_writes_destination_then_removes_source(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    destination = tmp_path / "archive" / "published.md"
    source.write_text("original", encoding="utf-8")

    atomic_publish(source, destination, "published")

    assert not source.exists()
    assert destination.read_text(encoding="utf-8") == "published"


def test_atomic_write_text_replaces_file(tmp_path: Path) -> None:
    path = tmp_path / "memory.md"
    path.write_text("old", encoding="utf-8")
    atomic_write_text(path, "new")
    assert path.read_text(encoding="utf-8") == "new"
