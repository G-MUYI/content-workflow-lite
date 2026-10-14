#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from workflow_config import ROOT
from workflow_lib import parse_frontmatter_document, read_text


def safe_target(raw_target: str) -> Path:
    target = Path(raw_target)
    if not target.is_absolute():
        target = ROOT / target
    target = target.resolve()
    if not target.is_relative_to(ROOT.resolve()):
        raise ValueError("目标目录必须位于当前内容制作工作区内")
    if not target.exists() or not target.is_dir():
        raise ValueError(f"目标目录不存在：{target}")
    return target


def structure_signature(path: Path) -> str:
    text = read_text(path)
    document = parse_frontmatter_document(text)
    keys = sorted(document.data.keys()) if document else []
    headings = re.findall(r"^#{1,4}\s+(.+?)\s*$", text, re.M)
    return json.dumps(
        {"keys": keys, "headings": headings},
        ensure_ascii=False,
        sort_keys=True,
    )


def choose_sample(files: list[Path], sample_size: int) -> list[Path]:
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in files:
        groups[structure_signature(path)].append(path)

    ordered_groups = sorted(
        groups.values(),
        key=lambda items: (len(items), items[0].as_posix()),
    )
    selected: list[Path] = []
    for group in ordered_groups:
        if len(selected) >= sample_size:
            break
        selected.append(group[0])

    if len(selected) < sample_size:
        for path in files:
            if path in selected:
                continue
            selected.append(path)
            if len(selected) >= sample_size:
                break
    return selected


def build_batches(files: list[Path]) -> list[list[Path]]:
    remaining = list(files)
    batches: list[list[Path]] = []
    while remaining:
        batch_size = min(20, max(1, math.ceil(len(remaining) * 0.25)))
        batches.append(remaining[:batch_size])
        remaining = remaining[batch_size:]
    return batches


def build_plan(
    target: Path,
    pattern: str = "*.md",
    workspace_root: Path | None = None,
) -> dict[str, object]:
    base = (workspace_root or ROOT).resolve()
    target = target.resolve()

    def relative(path: Path) -> str:
        return path.relative_to(base).as_posix()

    files = sorted(
        path
        for path in target.rglob(pattern)
        if path.is_file()
        and "_模板" not in path.parts
        and ".git" not in path.parts
    )
    signatures = Counter(structure_signature(path) for path in files)
    if not files:
        sample: list[Path] = []
        remainder: list[Path] = []
    else:
        sample_size = min(5, max(1, math.ceil(len(files) * 0.1)))
        sample = choose_sample(files, sample_size)
        remainder = [path for path in files if path not in sample]

    return {
        "level": "L0_read_only_audit",
        "target": relative(target),
        "total_files": len(files),
        "structure_variants": len(signatures),
        "sample_rule": "min(5, ceil(total × 10%)), at least 1",
        "sample_files": [relative(path) for path in sample],
        "expansion_batches": [
            [relative(path) for path in batch]
            for batch in build_batches(remainder)
        ],
        "required_validation": [
            "python scripts/validate-workflow.py",
            "python -m pytest -q",
            "相关结构审计脚本",
            "人工确认样本未丢失来源、正文或历史数据",
        ],
        "stop_conditions": [
            "连续出现 2 个同类错误",
            "任一数据丢失",
            "修改范围漂移",
            "校验错误数增加",
        ],
        "mutation_authorized": False,
        "next_step": "仅对 sample_files 执行 L1；L2 明确通过前不得运行 expansion_batches",
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="为历史内容批处理生成只读的分级扩张计划"
    )
    parser.add_argument("--target", required=True)
    parser.add_argument("--pattern", default="*.md")
    args = parser.parse_args()
    try:
        target = safe_target(args.target)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(build_plan(target, args.pattern), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
