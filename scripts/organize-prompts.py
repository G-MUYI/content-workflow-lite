#!/usr/bin/env python3

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from workflow_lib import (
    atomic_publish,
    atomic_write_text,
    parse_frontmatter_document,
    read_text,
    render_yaml_value,
    scalar_text,
    update_frontmatter_text,
)


ROOT = Path(__file__).resolve().parent.parent
PROMPT_ROOT = ROOT / "素材库" / "提示词"
INBOX_DIR = PROMPT_ROOT / "_inbox"
ORGANIZED_DIR = PROMPT_ROOT / "已整理"
TOPIC_ROOT = ROOT / "选题库"
TOPIC_INBOX_DIR = TOPIC_ROOT / "_inbox"
TOPIC_TEMPLATE = TOPIC_ROOT / "_模板" / "选题模板-标准.md"


def has_flag(name: str) -> bool:
    import sys

    return name in sys.argv


def read_arg(name: str) -> str:
    import sys

    argv = sys.argv[1:]
    for index, item in enumerate(argv):
        if item.startswith(f"{name}="):
            return item.split("=", 1)[1]
        if item == name and index + 1 < len(argv) and not argv[index + 1].startswith("--"):
            return argv[index + 1]
    return ""


def to_posix(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def parse_frontmatter(text: str):
    document = parse_frontmatter_document(text)
    if not document:
        return None
    raw = {}
    order = []
    for line in document.block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        raw[key.strip()] = value.strip()
        order.append(key.strip())
    return {
        "raw": raw,
        "order": order,
        "full_match": document.full_match,
        "data": document.data,
    }


def quote(value: str) -> str:
    return '"' + str(value or "").replace("\\", "\\\\").replace('"', '\\"') + '"'


def strip_quotes(value: str) -> str:
    value = str(value or "").strip()
    if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
        return value[1:-1]
    return value


def frontmatter_value(frontmatter: dict, key: str) -> str:
    return scalar_text(frontmatter.get("data", {}).get(key))


def get_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^### {re.escape(heading)}\s*$", re.M)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    rest = text[start:]
    next_match = re.search(r"\n### [^\n]+|\n## [^\n]+", rest)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def get_code_block(text: str, heading: str) -> str:
    section = get_section(text, heading)
    match = re.search(r"```(?:text)?\n([\s\S]*?)\n```", section)
    return match.group(1).strip() if match else section.strip()


def get_markdown_section(text: str, heading: str, level: int = 2) -> str:
    marks = "#" * level
    pattern = re.compile(rf"^{marks}\s+{re.escape(heading)}\s*$", re.M)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    rest = text[start:]
    next_match = re.search(rf"\n#{{1,{level}}}\s+[^\n]+", rest)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def replace_h2_section(text: str, heading: str, content: str) -> str:
    pattern = re.compile(rf"^(##\s+{re.escape(heading)}\s*\n)(.*?)(?=^##\s+|\Z)", re.S | re.M)
    return pattern.sub(lambda match: f"{match.group(1)}{content.strip()}\n\n---\n\n", text, count=1)


def section_has_value(text: str, heading: str) -> bool:
    content = get_section(text, heading)
    if not content:
        return False
    placeholders = {
        "（待后续整理成可复用提示词资产）",
        "（同步素材内容：保留原文、原链接、原备注）",
        "- 变量1：\n- 变量2：",
    }
    return content not in placeholders


def prompt_has_value(text: str) -> bool:
    content = get_code_block(text, "完整提示词")
    return bool(content and content not in {"", "（待补充）"})


def resolve_target(path: Path) -> Path:
    target = ORGANIZED_DIR / path.name
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    version = 2
    while True:
        candidate = target.with_name(f"{stem}_v{version}{suffix}")
        if not candidate.exists():
            return candidate
        version += 1


def sanitize_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\n\r\t]+', "-", value or "")
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:80] or "未命名提示词素材"


def resolve_topic_target(title: str) -> Path:
    TOPIC_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    target = TOPIC_INBOX_DIR / f"提示词素材-{sanitize_filename(title)}.md"
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    version = 2
    while True:
        candidate = target.with_name(f"{stem}_v{version}{suffix}")
        if not candidate.exists():
            return candidate
        version += 1


def content_source_id(path: Path, frontmatter: dict) -> str:
    existing = frontmatter_value(frontmatter, "source_id")
    return existing or f"prompt_asset:{path.stem}"


def find_existing_topic(source_id: str, content_angle: str = "prompt_list") -> Path | None:
    if not source_id or not TOPIC_ROOT.exists():
        return None
    for path in TOPIC_ROOT.rglob("*.md"):
        relative = to_posix(path)
        if "/_模板/" in relative:
            continue
        text = read_text(path)
        frontmatter = parse_frontmatter(text)
        if not frontmatter:
            continue
        if frontmatter_value(frontmatter, "source_id") == source_id and frontmatter_value(frontmatter, "content_angle") == content_angle:
            return path
    return None


def build_topic_frontmatter(title: str, frontmatter: dict, source_id: str) -> str:
    today = date.today().isoformat()
    source = frontmatter_value(frontmatter, "source") or "提示词素材库"
    source_type = frontmatter_value(frontmatter, "source_type") or "想法"
    tags = frontmatter.get("data", {}).get("tags") or []
    lines = [
        "---",
        f"title: {quote(title)}",
        'status: "todo"',
        'stage: "raw_idea"',
        'agent: "topic-master"',
        'priority: ""',
        'interrupt_type: ""',
        f"source: {quote(source)}",
        f"source_type: {quote(source_type)}",
        f"source_id: {quote(source_id)}",
        'workflow_mode: "standard"',
        'timeliness_level: "weak"',
        'recommended_path: "prompt_list"',
        'content_angle: "prompt_list"',
        'content_goal: "collect"',
        'content_form: "article"',
        "target_platforms: []",
        'primary_platform: ""',
        'brief_audience: ""',
        'brief_user_action: ""',
        'brief_core_promise: ""',
        'evidence_status: "partial"',
        f"created: {today}",
        f"updated: {today}",
        "published_platforms: []",
        'published_date: ""',
    ]
    rendered_tags = render_yaml_value(tags)
    tag_lines = [f"tags: {rendered_tags[0]}", *rendered_tags[1:]]
    created_index = lines.index(f"created: {today}")
    lines[created_index:created_index] = tag_lines
    lines.append("---")
    return "\n".join(lines) + "\n"


def build_topic_body(asset_path: Path, text: str, source_id: str) -> str:
    raw_material = get_markdown_section(text, "原始素材", level=2)
    prompt_breakdown = get_markdown_section(text, "提示词拆解", level=2)
    parts = [
        "<!-- ✏️ 写入者：topic-master | 阶段：raw_idea -->",
        "",
        f"来源提示词资产：`{to_posix(asset_path)}`",
        f"source_id：`{source_id}`",
        "",
        "### 原始素材摘录",
        "",
        raw_material or "（原提示词资产未填写原始素材）",
    ]
    if prompt_breakdown:
        parts.extend(["", "### 提示词拆解摘录", "", prompt_breakdown])
    return "\n".join(parts).strip()


def create_topic_handoff(asset_path: Path, text: str, frontmatter: dict, source_id: str) -> str:
    title = frontmatter_value(frontmatter, "title") or asset_path.stem
    existing = find_existing_topic(source_id)
    if existing:
        return to_posix(existing)

    template = read_text(TOPIC_TEMPLATE)
    topic_text = re.sub(r"^---\n.*?\n---\n?", build_topic_frontmatter(title, frontmatter, source_id), template, count=1, flags=re.S)
    topic_text = topic_text.replace("# [标题]", f"# {title}", 1)
    topic_text = replace_h2_section(topic_text, "原始素材", build_topic_body(asset_path, text, source_id))

    target = resolve_topic_target(title)
    atomic_write_text(target, topic_text)
    return to_posix(target)


def ensure_topic_handoff(asset_path: Path, text: str, frontmatter: dict) -> tuple[str, str]:
    source_id = content_source_id(asset_path, frontmatter)
    state = frontmatter_value(frontmatter, "content_handoff") or "pending"
    existing_handoff_file = frontmatter_value(frontmatter, "content_handoff_file")
    if state == "skipped":
        return source_id, existing_handoff_file
    if state == "done" and existing_handoff_file:
        candidate = (ROOT / existing_handoff_file).resolve()
        if candidate.exists() and candidate.is_file():
            candidate_text = read_text(candidate)
            candidate_frontmatter = parse_frontmatter(candidate_text)
            if (
                candidate_frontmatter
                and frontmatter_value(candidate_frontmatter, "source_id") == source_id
                and frontmatter_value(candidate_frontmatter, "content_angle") == "prompt_list"
            ):
                return source_id, to_posix(candidate)
    return source_id, create_topic_handoff(asset_path, text, frontmatter, source_id)


@dataclass
class PromptCheck:
    path: Path
    ready: bool
    reasons: list[str]
    target_path: Path | None = None
    suggestions: list[str] | None = None


def check_file(path: Path) -> PromptCheck:
    text = read_text(path)
    frontmatter = parse_frontmatter(text)
    reasons = []
    suggestions = []

    if not frontmatter:
        reasons.append("缺少 frontmatter")
        suggestions.append("先补标准 frontmatter，再进入整理流程。")
        return PromptCheck(path=path, ready=False, reasons=reasons, suggestions=suggestions)

    raw = frontmatter["raw"]
    title = raw.get("title", "").strip('"')
    if raw.get("material_type", "").replace('"', "") != "prompt_asset":
        reasons.append("material_type 不是 prompt_asset")
        suggestions.append("确认这是不是提示词资产；如果不是，改走知识卡片或网站收藏流程。")
    if not section_has_value(text, "适用场景"):
        reasons.append("缺少“适用场景”内容")
        suggestions.append(f"可先用标题《{title or path.stem}》概括一句：这条提示词适用于什么任务。")
    variables_text = get_section(text, "输入变量")
    if not variables_text or "变量1" in variables_text:
        reasons.append("输入变量仍是占位内容")
        suggestions.append("把原始素材里真正需要替换的 1-3 个参数写清楚，删掉“变量1/变量2”占位。")
    if not prompt_has_value(text):
        reasons.append("缺少“完整提示词”内容")
        suggestions.append("从原始素材中提取可直接复制的提示词，放进 ```text``` 代码块。")
    if not section_has_value(text, "使用说明"):
        reasons.append("缺少“使用说明”内容")
        suggestions.append("补一句怎么替换变量、在什么场景下使用、输出格式要注意什么。")
    if not section_has_value(text, "预期输出"):
        reasons.append("缺少“预期输出”内容")
        suggestions.append("写明最终希望 AI 输出什么，比如表格、清单、文案、JSON。")

    ready = len(reasons) == 0
    return PromptCheck(
        path=path,
        ready=ready,
        reasons=reasons,
        target_path=resolve_target(path) if ready else None,
        suggestions=suggestions,
    )


def iter_target_files(selected_file: str):
    if selected_file:
        path = (ROOT / selected_file).resolve()
        if path.exists() and path.is_file():
            yield path
        return

    if not INBOX_DIR.exists():
        return

    for path in sorted(INBOX_DIR.glob("*.md")):
        if path.is_file():
            yield path


def apply_move(check: PromptCheck) -> str:
    text = read_text(check.path)
    frontmatter = parse_frontmatter(text)
    if not frontmatter or not check.target_path:
        return ""

    source_id, handoff_file = ensure_topic_handoff(check.path, text, frontmatter)
    updates = {
        "status": "done",
        "stage": "organized",
        "agent": "prompt-librarian",
        "updated": date.today().isoformat(),
    }
    if source_id and not frontmatter_value(frontmatter, "source_id"):
        updates["source_id"] = source_id
    if handoff_file:
        updates["content_handoff"] = "done"
        updates["content_handoff_file"] = handoff_file
    elif "content_handoff" not in frontmatter.get("data", {}):
        updates["content_handoff"] = "pending"
        updates["content_handoff_file"] = ""

    next_text = update_frontmatter_text(text, updates)
    atomic_publish(check.path, check.target_path, next_text)
    return handoff_file


def main():
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    selected_file = read_arg("--file")
    apply_mode = has_flag("--apply")
    suggest_mode = has_flag("--suggest")

    checks = [check_file(path) for path in iter_target_files(selected_file)]
    ready_items = [item for item in checks if item.ready]
    pending_items = [item for item in checks if not item.ready]

    mode = "apply" if apply_mode else "suggest" if suggest_mode else "check"
    print(f"提示词整理归档 | 模式: {mode}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"- 待检查文件: {len(checks)}")
    print(f"- 可归档: {len(ready_items)}")
    print(f"- 待完善: {len(pending_items)}")

    for item in ready_items:
        target = to_posix(item.target_path) if item.target_path else "-"
        print(f"READY {to_posix(item.path)} -> {target}")

    for item in pending_items:
        print(f"PENDING {to_posix(item.path)} | {'；'.join(item.reasons)}")
        if suggest_mode and item.suggestions:
            for suggestion in item.suggestions:
                print(f"  SUGGEST {suggestion}")

    if apply_mode and ready_items:
        handoff_files = []
        for item in ready_items:
            handoff_file = apply_move(item)
            if handoff_file:
                handoff_files.append(handoff_file)
        print(f"✅ 已归档 {len(ready_items)} 个提示词文件")
        if handoff_files:
            print(f"✅ 已同步转交 {len(handoff_files)} 个选题素材")
            for handoff_file in handoff_files:
                print(f"  TOPIC {handoff_file}")
    elif apply_mode:
        print("✅ 当前没有可归档的提示词文件")


if __name__ == "__main__":
    main()
