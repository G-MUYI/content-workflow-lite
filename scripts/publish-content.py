#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from workflow_config import CONTENT_ROOT, MATERIAL_ROOT, ROOT
from workflow_lib import (
    atomic_publish,
    atomic_write_text,
    parse_frontmatter_document,
    read_text,
    relative_posix,
    resolve_versioned_path,
    scalar_text,
    update_frontmatter_text,
)


@dataclass
class PublishTarget:
    source: Path
    destination: Path
    title: str
    content: str


def has_flag(name: str) -> bool:
    return name in sys.argv


def read_arg(name: str) -> str:
    argv = sys.argv[1:]
    for index, item in enumerate(argv):
        if item.startswith(f"{name}="):
            return item.split("=", 1)[1]
        if item == name and index + 1 < len(argv) and not argv[index + 1].startswith("--"):
            return argv[index + 1]
    return ""


def to_posix(path: Path) -> str:
    return relative_posix(path, ROOT)


def strip_quotes(value: str) -> str:
    value = str(value or "").strip()
    if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
        return value[1:-1]
    return value


def quote(value: str) -> str:
    return '"' + str(value or "").replace("\\", "\\\\").replace('"', '\\"') + '"'


def parse_list(value: str) -> list[str]:
    raw = strip_quotes(value)
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [item.strip().strip('"').strip("'") for item in raw.split(",") if item.strip()]


PLATFORM_ALIASES = {
    "公众号": "wechat",
    "微信": "wechat",
    "微信公众号": "wechat",
    "wechat": "wechat",
    "weixin": "wechat",
    "小红书": "xiaohongshu",
    "xhs": "xiaohongshu",
    "xiaohongshu": "xiaohongshu",
    "知乎": "zhihu",
    "zhihu": "zhihu",
    "朋友圈": "moments",
    "moments": "moments",
    "x": "x",
    "twitter": "x",
    "即刻": "jike",
    "jike": "jike",
}


def normalize_platforms(values: list[str]) -> list[str]:
    normalized = []
    for value in values:
        key = value.strip()
        platform = PLATFORM_ALIASES.get(key.lower(), PLATFORM_ALIASES.get(key, key))
        if platform and platform not in normalized:
            normalized.append(platform)
    return normalized


def build_list(values: list[str]) -> str:
    clean = [item.strip() for item in values if item.strip()]
    return "[" + ", ".join(clean) + "]"


def candidate_files() -> list[Path]:
    root = CONTENT_ROOT / "进行中"
    if not root.exists():
        return []
    candidates = []
    for path in sorted(root.glob("*.md")):
        text = read_text(path)
        document = parse_frontmatter_document(text)
        if not document:
            continue
        if scalar_text(document.data.get("stage")) == "reviewed":
            candidates.append(path)
    return candidates


def resolve_file(value: str) -> Path | None:
    if value:
        path = (ROOT / value).resolve()
        if path.exists() and path.is_file():
            return path
        matches = [item for item in (CONTENT_ROOT / "进行中").glob("*.md") if value in item.stem]
        if len(matches) == 1:
            return matches[0]
        return None

    candidates = candidate_files()
    if len(candidates) == 1:
        return candidates[0]
    return None


def ensure_publish_section(text: str) -> str:
    match = re.search(r"^##\s+发布后数据\s*$", text, re.M)
    if match:
        if "**数据填写状态**" in text:
            return text
        next_match = re.search(r"\n##\s+[^\n]+", text[match.end() :])
        insert_at = match.end() + next_match.start() if next_match else len(text)
        return f"{text[:insert_at].rstrip()}\n\n**数据填写状态**：未填写\n{text[insert_at:]}"
    section = "\n".join(
        [
            "## 发布后数据",
            "",
            "| 平台 | 记录日期 | 阅读量 | 点赞 | 收藏 | 备注（可选） |",
            "|------|---------|-------|------|------|-------------|",
            "| | | | | | |",
            "",
            "> 每个平台只需填写一次最新快照；评论、转发等特殊指标可写进备注。",
            "",
            "**数据填写状态**：未填写",
            "",
            "---",
        ]
    )
    return f"{text.rstrip()}\n\n{section}\n"


def ensure_publish_followup(text: str) -> str:
    note = f"发布后提炼: {date.today().isoformat()} | 状态: 待知识园丁提炼金句/概念/结构"
    if "发布后提炼:" in text:
        return text
    if re.search(r"^##\s+写作笔记\s*$", text, re.M):
        return re.sub(r"(^##\s+写作笔记\s*$)", rf"\1\n\n- {note}", text, count=1, flags=re.M)
    return f"{text.rstrip()}\n\n## 写作笔记\n\n- {note}\n"


def build_target(path: Path, platforms: list[str], published_date: str) -> PublishTarget | None:
    text = read_text(path)
    document = parse_frontmatter_document(text)
    if not document:
        return None
    stage = scalar_text(document.data.get("stage"))
    if stage != "reviewed":
        raise ValueError(f"{to_posix(path)} 当前 stage={stage or '(空)'}，只有 reviewed 才能归档发布")

    title = scalar_text(document.data.get("title")) or path.stem
    next_text = update_frontmatter_text(
        text,
        {
            "status": "done",
            "stage": "published",
            "updated": published_date,
            "published_platforms": platforms,
            "published_date": published_date,
        },
    )
    next_document = parse_frontmatter_document(next_text)
    if not next_document:
        raise ValueError("发布更新后 frontmatter 无法解析")
    next_body = ensure_publish_followup(ensure_publish_section(next_document.body))
    next_text = f"---\n{next_document.block}\n---\n{next_body.lstrip()}"
    raw_destination = CONTENT_ROOT / "已发布" / published_date[:4] / published_date[5:7] / path.name
    destination = resolve_versioned_path(raw_destination)
    return PublishTarget(path, destination, title, next_text)


def update_handoff_references(source: Path, destination: Path) -> tuple[int, list[str]]:
    source_ref = to_posix(source)
    destination_ref = to_posix(destination)
    updated = 0
    warnings: list[str] = []
    if not MATERIAL_ROOT.exists():
        return updated, warnings

    for path in MATERIAL_ROOT.rglob("*.md"):
        try:
            text = read_text(path)
            document = parse_frontmatter_document(text)
            if not document:
                continue
            if scalar_text(document.data.get("content_handoff_file")) != source_ref:
                continue
            next_text = update_frontmatter_text(text, {"content_handoff_file": destination_ref})
            atomic_write_text(path, next_text)
            updated += 1
        except Exception as error:
            warnings.append(f"{to_posix(path)} 回写失败：{error}")
    return updated, warnings


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    selected = read_arg("--file")
    platforms = normalize_platforms(parse_list(read_arg("--platforms") or read_arg("--platform")))
    published_date = read_arg("--date") or date.today().isoformat()
    apply_mode = has_flag("--apply")
    path = resolve_file(selected)

    if not platforms:
        print("发布归档需要明确平台。请加参数，例如：--platforms wechat / xiaohongshu / zhihu")
        raise SystemExit(1)

    try:
        datetime.strptime(published_date, "%Y-%m-%d")
    except ValueError:
        print("发布归档失败：--date 必须使用 YYYY-MM-DD")
        raise SystemExit(1)

    if not path:
        candidates = candidate_files()
        print("发布归档需要明确目标文件。")
        if candidates:
            print("可发布候选：")
            for item in candidates:
                print(f"- {to_posix(item)}")
        else:
            print("当前没有 stage=reviewed 的进行中文件。")
        raise SystemExit(1)

    try:
        target = build_target(path, platforms, published_date)
    except ValueError as error:
        print(f"发布归档失败：{error}")
        raise SystemExit(1)

    if not target:
        print("发布归档失败：目标文件缺少 frontmatter")
        raise SystemExit(1)

    print("发布归档预检")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"- 标题: {target.title}")
    print(f"- 来源: {to_posix(target.source)}")
    print(f"- 目标: {to_posix(target.destination)}")
    print(f"- 平台: {', '.join(platforms)}")
    print(f"- 日期: {published_date}")

    if not apply_mode:
        print("未写入。确认无误后执行：python scripts/publish-content.py --apply --platforms 平台 --file \"路径\"")
        return

    try:
        atomic_publish(target.source, target.destination, target.content)
    except Exception as error:
        print(f"发布归档失败，源文件保持不变：{error}")
        raise SystemExit(1)

    backlink_count, backlink_warnings = update_handoff_references(target.source, target.destination)
    print("✅ 已归档到已发布目录")
    if backlink_count:
        print(f"✅ 已更新 {backlink_count} 个 content_handoff_file 引用")
    for warning in backlink_warnings:
        print(f"⚠️ {warning}")
    print("📌 已在写作笔记中标记发布后提炼待办，请继续调用知识园丁提炼素材。")


if __name__ == "__main__":
    main()
