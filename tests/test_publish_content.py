from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from scripts.workflow_lib import atomic_publish, parse_frontmatter_document


ROOT = Path(__file__).resolve().parents[1]


def load_publish_module():
    path = ROOT / "scripts" / "publish-content.py"
    spec = importlib.util.spec_from_file_location("publish_content_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_publish_preserves_yaml_lists_and_updates_handoff(tmp_path: Path) -> None:
    publish = load_publish_module()
    publish.ROOT = tmp_path
    publish.CONTENT_ROOT = tmp_path / "选题库"
    publish.MATERIAL_ROOT = tmp_path / "素材库"

    source = publish.CONTENT_ROOT / "进行中" / "文章.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        """---
title: "文章"
status: "in_progress"
stage: "reviewed"
agent: "content-reviewer"
tags:
  - "AI"
voice_anchors:
  - "包含: 冒号"
---

## 正文

正文。
""",
        encoding="utf-8",
    )
    asset = publish.MATERIAL_ROOT / "提示词" / "已整理" / "资产.md"
    asset.parent.mkdir(parents=True)
    asset.write_text(
        """---
source_id: "demo"
content_handoff: "done"
content_handoff_file: "选题库/进行中/文章.md"
---
""",
        encoding="utf-8",
    )

    target = publish.build_target(source, ["wechat"], "2026-07-27")
    assert target is not None
    document = parse_frontmatter_document(target.content)
    assert document is not None
    assert document.data["tags"] == ["AI"]
    assert document.data["voice_anchors"] == ["包含: 冒号"]
    assert document.data["agent"] == "content-reviewer"
    assert document.data["published_platforms"] == ["wechat"]

    atomic_publish(target.source, target.destination, target.content)
    count, warnings = publish.update_handoff_references(target.source, target.destination)
    assert count == 1
    assert warnings == []
    asset_document = parse_frontmatter_document(asset.read_text(encoding="utf-8"))
    assert asset_document is not None
    assert asset_document.data["content_handoff_file"] == "选题库/已发布/2026/07/文章.md"
