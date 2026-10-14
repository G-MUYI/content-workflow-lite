#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from workflow_config import CONTENT_ROOT, ROOT


PREFERRED_KEYS = [
    "title",
    "status",
    "stage",
    "agent",
    "priority",
    "interrupt_type",
    "source",
    "source_type",
    "source_id",
    "timeliness_level",
    "recommended_path",
    "content_angle",
    "content_goal",
    "content_form",
    "target_platforms",
    "tags",
    "created",
    "updated",
    "published_platforms",
    "published_date",
]

DEFAULTS = {
    "source_id": '""',
    "timeliness_level": '""',
    "recommended_path": '""',
    "content_angle": '""',
    "content_goal": '""',
    "content_form": '""',
    "target_platforms": "[]",
    "published_platforms": "[]",
    "published_date": '""',
}

ARCHIVED_DEFAULTS = {
    "agent": '""',
    "priority": '""',
    "interrupt_type": '""',
    "source": '""',
    "source_type": '""',
    "tags": "[]",
}


@dataclass
class Frontmatter:
    raw: dict[str, str]
    order: list[str]
    full_match: str


@dataclass
class MigrationTarget:
    path: Path
    relative: str
    operations: list[str]
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
    return path.relative_to(ROOT).as_posix()


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return path.read_text(encoding=encoding).replace("\r\n", "\n")
        except Exception:
            continue
    return path.read_text(errors="ignore").replace("\r\n", "\n")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def parse_frontmatter(text: str) -> Frontmatter | None:
    match = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not match:
        return None

    raw = {}
    order = []
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        raw[key] = value.strip()
        order.append(key)
    return Frontmatter(raw=raw, order=order, full_match=match.group(0))


def get_unquoted(raw_value: str) -> str:
    value = str(raw_value or "").strip()
    if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
        return value[1:-1]
    return value


def quote(value: str) -> str:
    return '"' + str(value or "").replace("\\", "\\\\").replace('"', '\\"') + '"'


def parse_date_like(value: str) -> str:
    match = re.search(r"20\d{2}[.-]\d{1,2}[.-]\d{1,2}", str(value or ""))
    if not match:
        return ""
    year, month, day = match.group(0).replace(".", "-").split("-")
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def infer_priority_and_interrupt(relative: str) -> tuple[str, str]:
    base = Path(relative).stem
    match = re.match(r"^([SABC])级-([^-]+)-", base)
    if not match:
        return "", ""
    return match.group(1), match.group(2)


def infer_source_type(relative: str, text: str) -> str:
    if "-想法-" in relative:
        return "想法"
    if "-公众号-" in relative or "-X素材-" in relative:
        return "链接"
    if re.search(r"https?://", text):
        return "链接"
    return ""


def extract_heading_title(text: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.M)
    return match.group(1).strip() if match else ""


def extract_metadata_table_value(text: str, label: str) -> str:
    match = re.search(rf"\|\s*{re.escape(label)}\s*\|\s*([^|]+)\|", text)
    return match.group(1).strip() if match else ""


def build_archived_frontmatter(relative: str, text: str) -> str:
    heading_title = extract_heading_title(text) or Path(relative).stem
    priority, interrupt_type = infer_priority_and_interrupt(relative)
    created = (
        parse_date_like(extract_metadata_table_value(text, "创建日期"))
        or parse_date_like(relative)
        or "2026-01-01"
    )
    source = extract_metadata_table_value(text, "来源素材") or extract_metadata_table_value(text, "来源")
    source_type = infer_source_type(relative, text)
    lines = [
        "---",
        f"title: {quote(re.sub(r'^选题[:：]\\s*', '', heading_title))}",
        'status: "archived"',
        'stage: "archived"',
        'agent: "topic-master"',
        f"priority: {quote(priority)}",
        f"interrupt_type: {quote(interrupt_type)}",
        f"source: {quote(source)}",
        f"source_type: {quote(source_type)}",
        'source_id: ""',
        'timeliness_level: ""',
        'recommended_path: ""',
        'content_angle: ""',
        'content_goal: ""',
        'content_form: ""',
        "target_platforms: []",
        "tags: []",
        f"created: {created}",
        f"updated: {created}",
        "published_platforms: []",
        'published_date: ""',
        'archived_reason: "历史迁移补齐"',
        f"archived_date: {created}",
        "---",
    ]
    return "\n".join(lines) + "\n"


def detect_publish_date(frontmatter: Frontmatter) -> str:
    published_date = get_unquoted(frontmatter.raw.get("published_date", ""))
    if published_date:
        return frontmatter.raw["published_date"]
    candidate = get_unquoted(frontmatter.raw.get("updated", "")) or get_unquoted(frontmatter.raw.get("created", ""))
    return quote(candidate) if candidate else '""'


def detect_published_platforms(frontmatter: Frontmatter, body: str) -> str:
    existing = frontmatter.raw.get("published_platforms")
    if existing and existing != "[]":
        return existing
    if "| 在看 |" in body:
        return "[wechat]"
    return "[wechat]"


def rebuild_frontmatter(frontmatter: Frontmatter, body: str, is_published: bool = False, is_archived: bool = False) -> str:
    merged = dict(frontmatter.raw)
    if is_archived:
        for key, value in ARCHIVED_DEFAULTS.items():
            merged.setdefault(key, value)
    for key, value in DEFAULTS.items():
        merged.setdefault(key, value)
    if is_published:
        merged["published_platforms"] = detect_published_platforms(frontmatter, body)
        merged["published_date"] = detect_publish_date(frontmatter)

    lines = ["---"]
    for key in PREFERRED_KEYS:
        if key in merged:
            lines.append(f"{key}: {merged.pop(key)}")
    for key in frontmatter.order:
        if key in merged:
            lines.append(f"{key}: {merged.pop(key)}")
    for key, value in merged.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def walk_markdown_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.md") if path.is_file())


def get_section_range(text: str, heading: str) -> tuple[int, int] | None:
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.M)
    if not match:
        return None
    start = match.start()
    after_start = match.end()
    rest = text[after_start:]
    next_match = re.search(r"\n## [^\n]+", rest)
    end = after_start + next_match.start() + 1 if next_match else len(text)
    return start, end


def ensure_section_before(text: str, anchor_heading: str, heading: str, content: str) -> str:
    if re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.M):
        return text
    anchor = get_section_range(text, anchor_heading)
    if not anchor:
        return f"{text.rstrip()}\n\n{content.strip()}\n"
    start, _ = anchor
    return f"{text[:start].rstrip()}\n\n{content.strip()}\n\n{text[start:]}"


def extract_legacy_metric_value(line: str) -> str:
    cells = [item.strip() for item in line.split("|") if item.strip()]
    return cells[-1] if len(cells) > 1 else ""


def build_wechat_publish_section(comment_line: str, metrics: dict[str, str], data_state: str) -> str:
    rows = [
        ("阅读量", metrics.get("阅读量", "")),
        ("点赞", metrics.get("点赞", "")),
        ("在看", metrics.get("在看", "")),
        ("收藏", metrics.get("收藏", "")),
        ("评论", metrics.get("评论", "")),
    ]
    lines = ["## 发布后数据"]
    if comment_line:
        lines.append(comment_line)
    lines.extend(["", "### 微信公众号", "", "| 指标 | 24h | 72h | 7d |", "|------|-----|-----|-----|"])
    for metric, value in rows:
        lines.append(f"| {metric} | {value} | | |")
    lines.extend(
        [
            "",
            "### 小红书",
            "",
            "| 指标 | 24h | 72h | 7d |",
            "|------|-----|-----|-----|",
            "| 阅读量 | | | |",
            "| 点赞 | | | |",
            "| 收藏 | | | |",
            "| 评论 | | | |",
            "| 转发 | | | |",
            "",
            "### 知乎",
            "",
            "| 指标 | 24h | 72h | 7d |",
            "|------|-----|-----|-----|",
            "| 阅读量 | | | |",
            "| 点赞 | | | |",
            "| 收藏 | | | |",
            "| 评论 | | | |",
            "",
            "> 只填写已发布平台的数据，未发布平台留空",
            "",
            f"**数据填写状态**：{data_state}",
            "",
            "---",
        ]
    )
    return "\n".join(lines) + "\n"


def has_filled_data(text: str) -> bool:
    section_range = get_section_range(text, "发布后数据")
    if not section_range:
        return False
    start, end = section_range
    return bool(re.search(r"\|\s*\d+[\d,]*\s*\|", text[start:end]))


def migrate_publish_section(text: str) -> str:
    section_range = get_section_range(text, "发布后数据")
    if not section_range:
        return text
    start, end = section_range
    section = text[start:end]
    comment_match = re.search(r"<!--.*?-->", section, re.S)
    comment_line = comment_match.group(0) if comment_match else ""

    if "### 微信公众号" not in section:
        metrics = {}
        for line in section.splitlines():
            if not line.startswith("|") or "指标" in line or "------" in line:
                continue
            cells = [item.strip() for item in line.split("|") if item.strip()]
            if cells:
                metrics[cells[0]] = extract_legacy_metric_value(line)
        data_state = "已填写" if any(metrics.values()) else "未填写"
        replacement = build_wechat_publish_section(comment_line, metrics, data_state)
        return f"{text[:start]}{replacement}{text[end:]}"

    replacement = section.rstrip()
    changed = False
    if "**数据填写状态**" not in section:
        replacement = f"{replacement}\n\n**数据填写状态**：{'已填写' if has_filled_data(text) else '未填写'}"
        changed = True
    if not replacement.endswith("---"):
        replacement = f"{replacement}\n\n---"
        changed = True
    if not changed:
        return text
    return f"{text[:start]}{replacement}\n{text[end:].lstrip()}"


def add_legacy_compatibility_sections(text: str) -> str:
    sections = [
        (
            "原始素材",
            "\n".join(
                [
                    "## 原始素材",
                    "<!-- 兼容区块：历史文章迁移补齐 -->",
                    "",
                    "> 历史文章迁移补齐：原始素材未单独保留，请参考 YAML 中的 `source`、`source_type` 与正文内容。",
                ]
            ),
        ),
        (
            "选题评估",
            "\n".join(
                [
                    "## 选题评估",
                    "<!-- 兼容区块：历史文章迁移补齐 -->",
                    "",
                    "> 历史文章迁移补齐：旧版结构请参考本文中的 `## 6维度评估`、`## 核心洞见` 等区块。",
                ]
            ),
        ),
        (
            "内容策划",
            "\n".join(
                [
                    "## 内容策划",
                    "<!-- 兼容区块：历史文章迁移补齐 -->",
                    "",
                    "> 历史文章迁移补齐：旧版结构请参考本文中的 `## 内容结构` 或相关正文说明。",
                ]
            ),
        ),
        (
            "审稿记录",
            "\n".join(
                [
                    "## 审稿记录",
                    "<!-- 兼容区块：历史文章迁移补齐 -->",
                    "",
                    "| 项目 | 结果 |",
                    "|------|------|",
                    "| 日期 | 历史文章未保留标准审稿记录 |",
                    "| 等级 | - |",
                    "| 硬伤数 | - |",
                ]
            ),
        ),
    ]
    result = text
    for heading, content in sections:
        result = ensure_section_before(result, "发布后数据", heading, content)
    return result


def ensure_planned_sections(text: str) -> str:
    if "## 内容策划" not in text or "### 派活清单" in text:
        return text
    section_range = get_section_range(text, "内容策划")
    if not section_range:
        return text
    start, end = section_range
    section = text[start:end].rstrip()
    replacement = f"{section}\n\n### 派活清单\n\n（待补充）\n"
    return f"{text[:start]}{replacement}{text[end:]}"


def migrate_file(path: Path, scope: str) -> MigrationTarget | None:
    relative = to_posix(path)
    if "/_模板/" in relative or relative.endswith("/README.md"):
        return None

    top_dir = relative.split("/")[1] if len(relative.split("/")) > 1 else ""
    is_active = top_dir in {"_inbox", "待写", "进行中"}
    is_published = top_dir == "已发布"
    is_archived = top_dir == "已弃用"

    if scope == "active" and not is_active:
        return None
    if scope == "published" and not is_published:
        return None
    if scope == "archived" and not is_archived:
        return None

    original = read_text(path)
    frontmatter = parse_frontmatter(original)
    if not frontmatter and not is_archived:
        return None

    body = original[len(frontmatter.full_match) :] if frontmatter else original
    next_body = body
    operations = []

    next_frontmatter = rebuild_frontmatter(frontmatter, body, is_published, is_archived) if frontmatter else build_archived_frontmatter(relative, original)
    if not frontmatter or next_frontmatter != frontmatter.full_match:
        operations.append("frontmatter")

    if is_active:
        updated_body = ensure_planned_sections(next_body)
        if updated_body != next_body:
            next_body = updated_body
            operations.append("sections")

    if is_published:
        updated_body = migrate_publish_section(next_body)
        updated_body = add_legacy_compatibility_sections(updated_body)
        if updated_body != next_body:
            next_body = updated_body
            operations.append("published-sections")

    if is_archived and not frontmatter:
        next_body = "\n" + next_body.lstrip()

    if not operations:
        return None

    return MigrationTarget(path=path, relative=relative, operations=operations, content=f"{next_frontmatter}{next_body.lstrip() if next_body.startswith(chr(10)) else next_body}")


def get_targets(scope: str) -> list[MigrationTarget]:
    return [target for path in walk_markdown_files(CONTENT_ROOT) if (target := migrate_file(path, scope))]


def print_summary(scope: str, targets: list[MigrationTarget], apply_mode: bool) -> None:
    print(f"内容 schema 迁移 | 范围: {scope} | 模式: {'apply' if apply_mode else 'check'}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"- 待处理文件: {len(targets)}")
    if not targets:
        print("✅ 当前范围内没有待迁移文件")
        return
    for target in targets:
        print(f"- {target.relative} | {', '.join(target.operations)}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    scope = read_arg("--scope") or "active,published,archived"
    apply_mode = has_flag("--apply")

    targets: list[MigrationTarget] = []
    for item in [part.strip() for part in scope.split(",") if part.strip()]:
        targets.extend(get_targets(item))

    unique_targets = []
    seen = set()
    for target in targets:
        if target.path in seen:
            continue
        seen.add(target.path)
        unique_targets.append(target)

    print_summary(scope, unique_targets, apply_mode)
    if apply_mode:
        for target in unique_targets:
            write_text(target.path, target.content)
        print(f"✅ 已写入 {len(unique_targets)} 个文件")


if __name__ == "__main__":
    main()
