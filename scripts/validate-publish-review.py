#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from workflow_lib import parse_frontmatter_document, read_text


ROOT = Path(__file__).resolve().parent.parent
PUBLISHED_ROOT = ROOT / "选题库" / "已发布"
STATS_ROOT = ROOT / "数据统计"
TEMPLATE_PATH = STATS_ROOT / "复盘记录-模板.md"


def parse_frontmatter(text: str):
    document = parse_frontmatter_document(text)
    if not document:
        return {}
    return document.data


def strip_quotes(value: str) -> str:
    value = str(value or "").strip()
    if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
        return value[1:-1]
    return value


def parse_date(value: str):
    value = strip_quotes(value)
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", value)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def walk_markdown_files(root: Path):
    if not root.exists():
        return []
    return sorted([path for path in root.rglob("*.md") if path.is_file()])


def to_posix(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


@dataclass
class Finding:
    level: str
    code: str
    path: str
    message: str


def collect_numeric_values(section: str) -> list[int]:
    values = []
    for match in re.finditer(r"\|\s*([0-9][0-9,]*)\s*\|", section):
        try:
            values.append(int(match.group(1).replace(",", "")))
        except ValueError:
            continue
    return values


def extract_section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.M)
    if not match:
        return ""
    start = match.end()
    rest = text[start:]
    next_match = re.search(r"\n## [^\n]+", rest)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end]


def validate_published_files(findings: list[Finding]):
    published_files = walk_markdown_files(PUBLISHED_ROOT)
    published_count = len(published_files)
    data_count = 0

    for path in published_files:
        text = read_text(path)
        frontmatter = parse_frontmatter(text)
        relative = to_posix(path)

        if strip_quotes(frontmatter.get("stage", "")) != "published":
            findings.append(Finding("error", "publish.stage_invalid", relative, "已发布文件的 stage 应为 published"))
        if strip_quotes(frontmatter.get("status", "")) != "done":
            findings.append(Finding("error", "publish.status_invalid", relative, "已发布文件的 status 应为 done"))
        if not strip_quotes(frontmatter.get("published_date", "")):
            findings.append(Finding("error", "publish.date_missing", relative, "缺少 published_date"))

        platforms_value = frontmatter.get("published_platforms", "")
        platforms = platforms_value if isinstance(platforms_value, list) else strip_quotes(platforms_value)
        if not platforms or platforms == "[]":
            findings.append(Finding("error", "publish.platforms_missing", relative, "缺少 published_platforms"))

        publish_section = extract_section(text, "发布后数据")
        review_section = extract_section(text, "复盘")
        if not publish_section:
            findings.append(Finding("error", "publish.section_missing", relative, "缺少 ## 发布后数据 区块"))
            continue

        if "**数据填写状态**" not in publish_section:
            findings.append(Finding("error", "publish.data_state_missing", relative, "缺少 数据填写状态 标记"))

        values = collect_numeric_values(publish_section)
        has_data = len(values) > 0
        if has_data:
            data_count += 1
        state = "未填写"
        state_match = re.search(r"\*\*数据填写状态\*\*[：:]\s*(\S+)", publish_section)
        if state_match:
            state = state_match.group(1)

        if has_data and state != "已填写":
            findings.append(Finding("warn", "publish.data_state_mismatch", relative, "已有数据但 数据填写状态 不是“已填写”"))
        if not has_data and state == "已填写":
            findings.append(Finding("warn", "publish.data_state_mismatch", relative, "数据填写状态 为“已填写”，但未检测到数值"))

        published_date = parse_date(frontmatter.get("published_date", ""))
        if published_date and (date.today() - published_date).days > 3 and state != "已填写":
            findings.append(Finding("warn", "publish.data_overdue", relative, "发布超过 3 天但仍未填写发布后数据"))

        if not review_section:
            findings.append(Finding("warn", "review.section_missing", relative, "缺少 ## 复盘 区块"))
        else:
            if "6维度回顾" in review_section:
                findings.append(Finding("warn", "review.legacy_six_dimensions", relative, "复盘区块仍使用 6维度 回顾"))
            if "7维度回顾" not in review_section:
                findings.append(Finding("warn", "review.seven_dimensions_missing", relative, "复盘区块尚未使用 7维度 回顾"))

        if re.search(r"^#{2,3}\s+6维度评估", text, re.M):
            findings.append(Finding("warn", "publish.legacy_six_dimension_eval", relative, "正文中的评估区块仍使用 6维度 标题"))
        if "认知颠覆" in text or "情绪共振" in text or "你独有" in text or "可写性" in text:
            findings.append(Finding("warn", "publish.legacy_dimension_terms", relative, "正文中仍包含旧版维度术语"))

    return published_count, data_count


def validate_review_files(findings: list[Finding], published_count: int, data_count: int):
    review_files = [path for path in walk_markdown_files(STATS_ROOT) if path.name != "复盘记录-模板.md"]
    latest_review_date = None

    if TEMPLATE_PATH.exists():
        template_text = read_text(TEMPLATE_PATH)
        if "6维度" in template_text:
            findings.append(Finding("warn", "review.template_legacy", to_posix(TEMPLATE_PATH), "复盘模板仍然包含 6维度 文案"))
        if "7维度" not in template_text:
            findings.append(Finding("warn", "review.template_missing", to_posix(TEMPLATE_PATH), "复盘模板尚未切换到 7维度 文案"))

    for path in review_files:
        text = read_text(path)
        relative = to_posix(path)
        if "复盘日期" not in text:
            findings.append(Finding("warn", "review.date_missing", relative, "复盘文件缺少 复盘日期"))

        if "6维度回顾" in text or "6维度预判准确度" in text or "对比发布前的6维度评估" in text:
            findings.append(Finding("warn", "review.legacy_six_dimensions", relative, "复盘文件仍包含 6维度 核心文案"))
        if "7维度回顾" not in text and "7维度预判准确度" not in text:
            findings.append(Finding("warn", "review.seven_dimensions_missing", relative, "复盘文件尚未使用 7维度 文案"))

        frontmatter = parse_frontmatter(text)
        candidate = parse_date(frontmatter.get("created", ""))
        if not candidate:
            match = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
            if match:
                candidate = datetime.strptime(match.group(1), "%Y-%m-%d").date()
            else:
                match = re.search(r"(20\d{2}-\d{2}-W\d+)", path.name)
                if match:
                    # fallback to file modified date for weekly file names
                    candidate = date.fromtimestamp(path.stat().st_mtime)
        if candidate and (latest_review_date is None or candidate > latest_review_date):
            latest_review_date = candidate

    if data_count >= 3 and latest_review_date is None:
        findings.append(Finding("warn", "review.missing", "数据统计", f"已有 {data_count} 篇有效数据，但未检测到复盘记录"))


def print_report(findings: list[Finding]):
    errors = [item for item in findings if item.level == "error"]
    warnings = [item for item in findings if item.level == "warn"]

    print("发布 / 复盘校验报告")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"- 错误: {len(errors)}")
    print(f"- 警告: {len(warnings)}")

    if not findings:
        print("✅ 当前没有发现发布 / 复盘问题")
        return

    for item in findings:
        prefix = "ERROR" if item.level == "error" else "WARN"
        print(f"{prefix} {item.path} | {item.code} | {item.message}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    findings: list[Finding] = []
    published_count, data_count = validate_published_files(findings)
    validate_review_files(findings, published_count, data_count)

    findings.sort(key=lambda item: (item.level != "error", item.path, item.code))

    if "--json" in sys.argv:
        print(
            json.dumps(
                {
                    "errors": len([item for item in findings if item.level == "error"]),
                    "warnings": len([item for item in findings if item.level == "warn"]),
                    "findings": [item.__dict__ for item in findings],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_report(findings)

    sys.exit(1 if any(item.level == "error" for item in findings) else 0)


if __name__ == "__main__":
    main()
