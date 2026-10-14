from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml


FRONTMATTER_RE = re.compile(r"\A---\n(?P<block>.*?)\n---\n?", re.S)
TOP_LEVEL_KEY_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*):(?:\s|$)")


@dataclass(frozen=True)
class FrontmatterDocument:
    data: dict[str, Any]
    block: str
    body: str
    full_match: str


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").replace("\r\n", "\n")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def parse_frontmatter_document(text: str) -> FrontmatterDocument | None:
    normalized = text.replace("\r\n", "\n")
    match = FRONTMATTER_RE.match(normalized)
    if not match:
        return None
    loaded = yaml.safe_load(match.group("block")) or {}
    if not isinstance(loaded, dict):
        raise ValueError("frontmatter 顶层必须是 YAML mapping")
    return FrontmatterDocument(
        data=loaded,
        block=match.group("block"),
        body=normalized[match.end() :],
        full_match=match.group(0),
    )


def scalar_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, dict)):
        return ""
    return str(value)


def render_yaml_value(value: Any) -> list[str]:
    if isinstance(value, str):
        return [yaml.safe_dump(value, allow_unicode=True, default_style='"').strip()]
    if isinstance(value, date):
        return [value.isoformat()]
    if value is None:
        return ['""']
    if isinstance(value, list):
        if not value:
            return ["[]"]
        rendered = yaml.safe_dump(
            value,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        ).rstrip()
        return [""] + rendered.splitlines()
    if isinstance(value, dict):
        if not value:
            return ["{}"]
        rendered = yaml.safe_dump(
            value,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        ).rstrip()
        return [""] + [f"  {line}" if line else line for line in rendered.splitlines()]
    return [yaml.safe_dump(value, allow_unicode=True, default_flow_style=True).strip()]


def _top_level_ranges(lines: list[str]) -> dict[str, tuple[int, int]]:
    starts: list[tuple[str, int]] = []
    for index, line in enumerate(lines):
        match = TOP_LEVEL_KEY_RE.match(line)
        if match:
            starts.append((match.group("key"), index))

    ranges: dict[str, tuple[int, int]] = {}
    for position, (key, start) in enumerate(starts):
        end = starts[position + 1][1] if position + 1 < len(starts) else len(lines)
        ranges[key] = (start, end)
    return ranges


def update_frontmatter_text(text: str, updates: dict[str, Any]) -> str:
    document = parse_frontmatter_document(text)
    if not document:
        raise ValueError("缺少有效 frontmatter")

    lines = document.block.splitlines()
    for key, value in updates.items():
        ranges = _top_level_ranges(lines)
        rendered_value = render_yaml_value(value)
        replacement = [f"{key}: {rendered_value[0]}"]
        replacement.extend(rendered_value[1:])

        if key in ranges:
            start, end = ranges[key]
            lines[start:end] = replacement
        else:
            lines.extend(replacement)

    block = "\n".join(lines)
    # 写回前再解析一次，避免生成损坏的 YAML。
    loaded = yaml.safe_load(block) or {}
    if not isinstance(loaded, dict):
        raise ValueError("更新后的 frontmatter 不是有效 mapping")
    return f"---\n{block}\n---\n{document.body.lstrip()}"


def resolve_versioned_path(target: Path) -> Path:
    if not target.exists():
        return target
    version = 2
    while True:
        candidate = target.with_name(f"{target.stem}_v{version}{target.suffix}")
        if not candidate.exists():
            return candidate
        version += 1


def atomic_publish(source: Path, destination: Path, content: str) -> None:
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(source)
    if destination.exists():
        raise FileExistsError(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
        )
        temp_path = Path(temp_name)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        # 临时文件必须可重新读取并保持 UTF-8。
        read_text(temp_path)
        os.replace(temp_path, destination)
        temp_path = None
        try:
            source.unlink()
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temp_path = Path(temp_name)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        read_text(temp_path)
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()
