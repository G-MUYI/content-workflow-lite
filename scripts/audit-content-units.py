#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from workflow_config import (
    CONTENT_UNIT_RELATIONS,
    CONTENT_UNIT_TYPES,
    MATERIAL_ROOT,
    ROOT,
)
from workflow_lib import parse_frontmatter_document, read_text, scalar_text


@dataclass
class Finding:
    level: str
    code: str
    path: str
    message: str


def frontmatter(path: Path) -> dict[str, str]:
    document = parse_frontmatter_document(read_text(path))
    if not document:
        return {}
    return {key: scalar_text(value) for key, value in document.data.items()}


def relation_rows(text: str) -> list[tuple[str, str, str]]:
    match = re.search(
        r"^##\s+关系\s*$\n(.*?)(?=^##\s+|\Z)",
        text,
        re.M | re.S,
    )
    if not match:
        return []
    rows: list[tuple[str, str, str]] = []
    for line in match.group(1).splitlines():
        if not line.strip().startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] == "关系":
            continue
        if not cells[0] and not cells[1]:
            continue
        rows.append((cells[0], cells[1], cells[3]))
    return rows


def audit_units(root: Path | None = None) -> dict[str, object]:
    scan_root = root or MATERIAL_ROOT / "知识卡片"
    files = sorted(scan_root.rglob("*.md")) if scan_root.exists() else []
    units: dict[str, tuple[Path, dict[str, str], list[tuple[str, str, str]]]] = {}
    findings: list[Finding] = []

    for path in files:
        data = frontmatter(path)
        if data.get("material_type") != "content_unit":
            continue
        unit_id = data.get("unit_id", "")
        unit_type = data.get("unit_type", "")
        relative = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()
        if not re.fullmatch(r"CU-\d{8}-\d{3,}", unit_id):
            findings.append(Finding("error", "unit.id_invalid", relative, f"unit_id 无效：{unit_id or '缺失'}"))
        elif unit_id in units:
            findings.append(Finding("error", "unit.id_duplicate", relative, f"unit_id 重复：{unit_id}"))
        if unit_type not in CONTENT_UNIT_TYPES:
            findings.append(Finding("error", "unit.type_invalid", relative, f"unit_type 无效：{unit_type or '缺失'}"))
        if "## 关系" not in read_text(path):
            findings.append(Finding("error", "unit.relations_missing", relative, "缺少 ## 关系"))
        if unit_id:
            units[unit_id] = (path, data, relation_rows(read_text(path)))

    active_relations: set[tuple[str, str, str]] = set()
    for unit_id, (path, _, rows) in units.items():
        relative = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()
        for relation, target, status in rows:
            if relation not in CONTENT_UNIT_RELATIONS:
                findings.append(Finding("error", "unit.relation_invalid", relative, f"关系类型无效：{relation}"))
                continue
            if status not in {"candidate", "active", "rejected"}:
                findings.append(Finding("error", "unit.relation_status_invalid", relative, f"关系状态无效：{status}"))
            if status == "active":
                active_relations.add((unit_id, relation, target))
                if target not in units:
                    findings.append(Finding("error", "unit.target_missing", relative, f"active 关系目标不存在：{target}"))

    for source, relation, target in sorted(active_relations):
        if relation == "conflicts_with" and (target, relation, source) not in active_relations:
            path = units[source][0]
            relative = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()
            findings.append(Finding("warn", "unit.conflict_not_symmetric", relative, f"conflicts_with 应双向登记：{target} → {source}"))

    return {
        "units": len(units),
        "errors": sum(item.level == "error" for item in findings),
        "warnings": sum(item.level == "warn" for item in findings),
        "findings": [asdict(item) for item in findings],
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    report = audit_units()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
