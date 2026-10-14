from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from scripts.workflow_lib import parse_frontmatter_document


ROOT = Path(__file__).resolve().parents[1]


def load_organizer_module():
    path = ROOT / "scripts" / "organize-prompts.py"
    spec = importlib.util.spec_from_file_location("organize_prompts_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_topic_handoff_frontmatter_preserves_prompt_tags() -> None:
    organizer = load_organizer_module()
    source = """---
title: "提示词"
source: "用户"
source_type: "想法"
tags:
  - "提示词"
  - "写作"
---
"""
    frontmatter = organizer.parse_frontmatter(source)
    assert frontmatter is not None
    result = organizer.build_topic_frontmatter("提示词", frontmatter, "demo")
    document = parse_frontmatter_document(result)
    assert document is not None
    assert document.data["tags"] == ["提示词", "写作"]
    assert document.data["workflow_mode"] == "standard"
