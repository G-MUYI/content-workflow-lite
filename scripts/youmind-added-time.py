#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from workflow_config import (
    YOUMIND_ADDED_TIME_UTC_OFFSET_HOURS,
    YOUMIND_DAILY_SOURCE_LIMIT,
    YOUMIND_SOURCE_BOARD,
)

LOCAL_TZ = timezone(timedelta(hours=YOUMIND_ADDED_TIME_UTC_OFFSET_HOURS))
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
# 页面发布日期常不标时区，按北京时间解析并放宽到全球时区最大偏差。
NAIVE_PUBLISHED_TOLERANCE = timedelta(hours=14)


def load_payload(input_path: str) -> dict[str, Any]:
    if input_path == "-":
        return json.load(sys.stdin)
    with Path(input_path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def decode_uuidv7(source_id: str) -> datetime | None:
    value = source_id.strip().lower()
    if not UUID_PATTERN.match(value):
        return None
    hex_value = value.replace("-", "")
    if hex_value[12] != "7" or hex_value[16] not in "89ab":
        return None
    milliseconds = int(hex_value[:12], 16)
    return datetime.fromtimestamp(milliseconds / 1000, tz=LOCAL_TZ)


def parse_published_at(raw: Any) -> tuple[datetime | None, bool]:
    text = str(raw or "").strip()
    if not text:
        return None, False
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=LOCAL_TZ), True
    return parsed, False


def check_source(source: dict[str, Any], now: datetime) -> dict[str, Any]:
    source_id = str(source.get("source_id", "")).strip()
    if not source_id:
        raise ValueError("每个来源必须包含非空 source_id")

    problems: list[str] = []
    added_at = decode_uuidv7(source_id)
    if added_at is None:
        problems.append("source_id 不是 UUIDv7，无法解码添加时间")
    elif added_at > now:
        problems.append("解码时间晚于当前时间")

    try:
        published_at, naive = parse_published_at(source.get("published_at"))
    except ValueError as exc:
        raise ValueError(f"来源 {source_id} 的 published_at 无效：{exc}") from exc
    if added_at and published_at:
        tolerance = NAIVE_PUBLISHED_TOLERANCE if naive else timedelta(0)
        if added_at + tolerance < published_at:
            problems.append("解码添加时间早于原帖发布时间")

    return {
        "source_id": source_id,
        "title": str(source.get("title", "")).strip(),
        "added_at": added_at.isoformat(timespec="seconds") if added_at else None,
        "method": "uuidv7_source_id",
        "verified": not problems,
        "problems": problems,
    }


def check_sources(payload: dict[str, Any], now: datetime) -> dict[str, Any]:
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("输入必须包含非空 sources 数组")

    checked = [check_source(source, now) for source in sources]
    decoded = [item for item in checked if item["added_at"]]
    # 展示时间保留到秒，排序仍使用 UUID 中的完整毫秒时间，避免同秒来源顺序错误。
    decoded.sort(key=lambda item: decode_uuidv7(item["source_id"]), reverse=True)
    ordered = decoded + [item for item in checked if not item["added_at"]]
    for index, item in enumerate(ordered, start=1):
        item["order"] = index

    return {
        "board": YOUMIND_SOURCE_BOARD,
        "limit": YOUMIND_DAILY_SOURCE_LIMIT,
        "verified": all(item["verified"] for item in ordered),
        "sources": ordered,
    }


def render_markdown(result: dict[str, Any]) -> str:
    board = result["board"]
    lines = [
        f"范围：YouMind「{board['name']}」（{board['board_id']}）；"
        "添加时间由 UUIDv7 source_id 解码（Asia/Shanghai）。",
        "",
        "| 顺序 | 标题 | source_id | 添加时间 | 核实 |",
        "|---:|---|---|---|---|",
    ]
    for item in result["sources"]:
        status = "通过" if item["verified"] else "失败：" + "；".join(item["problems"])
        lines.append(
            "| {order} | {title} | `{source_id}` | {added} | {status} |".format(
                added=item["added_at"] or "无法解码",
                status=status,
                **item,
            )
        )
    lines.append("")
    if result["verified"]:
        lines.append("**排序核实**：通过。")
    else:
        lines.append("**排序核实**：失败，按添加时间排序无法核实，停止采集。")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="由 UUIDv7 source_id 解码并核实 YouMind 来源添加时间"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="JSON 文件路径；- 表示 stdin")
    source.add_argument("--id", action="append", help="直接传入 source_id，可重复")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.input:
            payload = load_payload(args.input)
        else:
            payload = {"sources": [{"source_id": value} for value in args.id]}
        result = check_sources(payload, datetime.now(tz=LOCAL_TZ))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"来源输入无效：{exc}", file=sys.stderr)
        return 2

    if args.format == "markdown":
        print(render_markdown(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
