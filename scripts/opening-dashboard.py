#!/usr/bin/env python3

import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from workflow_config import (
    DELIVERY_TAIL_STAGES,
    DELIVERY_TAIL_WIP_LIMIT,
    NEXT_ACTION_STAGE_ORDER,
    QUICK_COMMAND_LINES,
)
from workflow_lib import parse_frontmatter_document, read_text, scalar_text


ROOT = Path(__file__).resolve().parent.parent
TOPIC_ROOT = ROOT / "选题库"
MATERIAL_ROOT = ROOT / "素材库"
STATS_ROOT = ROOT / "数据统计"
SESSION_FILE = ROOT / "skills" / "_通用" / "会话记忆.md"
PREFERENCES_FILE = ROOT / "skills" / "_通用" / "用户偏好.md"


def parse_frontmatter(path: Path) -> dict:
    text = read_text(path)
    document = parse_frontmatter_document(text)
    if not document:
        return {}
    return {key: scalar_text(value) for key, value in document.data.items()}


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


def days_since(value: str):
    target = parse_date(value)
    if not target:
        return None
    return (date.today() - target).days


def collect_files(folder: Path):
    if not folder.exists():
        return []
    return sorted([item for item in folder.glob("*.md") if item.is_file()])


def build_item(path: Path, bucket: str = "") -> dict:
    frontmatter = parse_frontmatter(path)
    return {
        "path": path,
        "title": strip_quotes(frontmatter.get("title", "")) or path.stem,
        "status": strip_quotes(frontmatter.get("status", "")),
        "stage": strip_quotes(frontmatter.get("stage", "")),
        "priority": strip_quotes(frontmatter.get("priority", "")),
        "created": strip_quotes(frontmatter.get("created", "")),
        "updated": strip_quotes(frontmatter.get("updated", "")),
        "published_date": strip_quotes(frontmatter.get("published_date", "")),
        "bucket": bucket,
    }


def collect_material_inbox_items():
    if not MATERIAL_ROOT.exists():
        return []

    items = []
    for inbox_dir in sorted(path for path in MATERIAL_ROOT.rglob("_inbox") if path.is_dir()):
        bucket = inbox_dir.parent.name
        for file_path in collect_files(inbox_dir):
            items.append(build_item(file_path, bucket=bucket))

    items.sort(
        key=lambda item: (
            parse_date(item["created"]) or date.min,
            item["bucket"],
            item["path"].name,
        )
    )
    return items


def find_latest_review_date():
    if not STATS_ROOT.exists():
        return None

    dates = []
    for path in STATS_ROOT.rglob("*.md"):
        if "模板" in path.name:
            continue
        frontmatter = parse_frontmatter(path)
        created = parse_date(frontmatter.get("created", ""))
        if created:
            dates.append(created)
            continue
        name_match = re.search(r"(20\d{2}-\d{2}-\d{2})", path.name)
        if name_match:
            dates.append(datetime.strptime(name_match.group(1), "%Y-%m-%d").date())
    return max(dates) if dates else None


def average(values):
    return round(sum(values) / len(values), 1) if values else None


def compute_next_action(stage: str, title: str) -> str:
    if stage == "drafted":
        return f"说“标题：{title}”"
    if stage == "titled":
        return f"说“审稿：{title}”"
    if stage == "reviewed":
        return f"说“发布到[平台]：{title}”"
    if stage == "assets_ready":
        return f"说“写：{title}”"
    if stage == "planned":
        return f"说“确认素材：{title}”"
    if stage == "strategies_generated":
        return f"说“策划：{title}”确认大纲"
    if stage == "checked_in":
        return f"说“策划：{title}”"
    return "继续推进"


def compute_suggestion(in_progress_items, todo_items, inbox_items, material_inbox_items, alarms):
    if alarms:
        return alarms[0]

    in_progress_suggestions = {
        "reviewed": "《{title}》已通过质检，可以发布了",
        "titled": "建议先审稿《{title}》",
        "drafted": "建议先给《{title}》起标题",
    }
    for stage in NEXT_ACTION_STAGE_ORDER:
        text = in_progress_suggestions.get(stage)
        if not text:
            continue
        for item in in_progress_items:
            if item["stage"] == stage:
                return text.format(title=item["title"])

    for stage, text in (
        ("assets_ready", "建议继续写《{title}》"),
        ("planned", "建议先确认《{title}》的素材支撑"),
        ("strategies_generated", "建议先确认《{title}》的大纲"),
        ("checked_in", "建议给《{title}》做内容策划"),
    ):
        for item in todo_items:
            if item["stage"] == stage:
                return text.format(title=item["title"])

    raw_ideas = [item for item in inbox_items if item["stage"] == "raw_idea"]
    if raw_ideas:
        if material_inbox_items:
            return f"选题 inbox 有 {len(raw_ideas)} 篇待处理，素材库 inbox 还有 {len(material_inbox_items)} 篇待整理"
        return f"inbox 有 {len(raw_ideas)} 篇素材待处理"

    if material_inbox_items:
        return f"素材库 inbox 有 {len(material_inbox_items)} 篇待整理"

    return "工作区 inbox 为空，可以开始投喂素材了"


def parse_ongoing_task():
    if not SESSION_FILE.exists():
        return ""
    text = read_text(SESSION_FILE)
    patterns = [
        r"## 当前进行中的任务\s+\n\s+\*\*(.+?)\*\*",
        r"\*\*当前进行中的任务\*\*[:：]?\s*(.+)",
        r"当前进行中的任务[:：]\s*(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.S)
        if match:
            value = match.group(1).strip()
            if value and value != "无":
                return value
    return ""


def memory_guardrail_counts() -> tuple[int, int]:
    if not SESSION_FILE.exists():
        return 0, 0
    text = read_text(SESSION_FILE)

    def section(name: str) -> str:
        match = re.search(
            rf"^##\s+{re.escape(name)}\s*$\n(.*?)(?=^##\s+|\Z)",
            text,
            re.M | re.S,
        )
        return match.group(1) if match else ""

    rejected = 0
    for line in section("用户已否决的方向").splitlines():
        if not line.strip().startswith("|") or "---" in line or "日期" in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[1] and cells[1] not in {"—", "暂无"}:
            rejected += 1

    hypotheses = 0
    for line in section("待验证假设").splitlines():
        if not line.strip().startswith("|") or "---" in line or "假设 ID" in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and cells[4] in {"candidate", "testing"}:
            hypotheses += 1
    return rejected, hypotheses


def build_dashboard():
    in_progress_items = [build_item(path) for path in collect_files(TOPIC_ROOT / "进行中")]
    todo_items = [build_item(path) for path in collect_files(TOPIC_ROOT / "待写")]
    inbox_items = [build_item(path) for path in collect_files(TOPIC_ROOT / "_inbox")]
    material_inbox_items = collect_material_inbox_items()
    published_items = [build_item(path) for path in sorted((TOPIC_ROOT / "已发布").rglob("*.md")) if path.is_file()]

    latest_review_date = find_latest_review_date()
    ongoing_task = parse_ongoing_task()
    rejected_count, hypothesis_count = memory_guardrail_counts()
    all_active = in_progress_items + todo_items + inbox_items
    stagnations = [days_since(item["updated"]) for item in all_active if days_since(item["updated"]) is not None]
    avg_stagnation = average(stagnations)

    if avg_stagnation is None:
        efficiency = "数据不足"
    elif avg_stagnation <= 3:
        efficiency = "✅ 健康"
    elif avg_stagnation <= 7:
        efficiency = "⚠️ 一般"
    else:
        efficiency = "🔴 需关注"

    stage_days = defaultdict(list)
    for item in all_active:
        stagnant = days_since(item["updated"])
        if stagnant is not None:
            stage_days[item["stage"] or "unknown"].append(stagnant)
    if stage_days:
        bottleneck_stage, values = max(stage_days.items(), key=lambda entry: sum(entry[1]))
        bottleneck = (
            f"{bottleneck_stage} ({len(values)} 篇，"
            f"累计停留 {sum(values)} 天，平均 {average(values)} 天)"
        )
    else:
        bottleneck = "无明显瓶颈"

    published_items_sorted = sorted(
        [item for item in published_items if parse_date(item.get("published_date", ""))],
        key=lambda item: parse_date(item.get("published_date", "")) or date.min,
        reverse=True,
    )
    completion_days = []
    for item in published_items_sorted[:5]:
        created = parse_date(item["created"])
        published = parse_date(item.get("published_date", ""))
        if created and published:
            completion_days.append(max(0, (published - created).days))
    avg_completion = average(completion_days) if len(completion_days) >= 3 else None

    today = date.today()
    month_done = sum(
        1
        for item in published_items
        if parse_date(item.get("published_date", ""))
        and parse_date(item.get("published_date", "")).year == today.year
        and parse_date(item.get("published_date", "")).month == today.month
    )

    alarms = []

    def add_alarm(rank: int, message: str):
        alarms.append((rank, message))

    tail_items = [item for item in all_active if item["stage"] in DELIVERY_TAIL_STAGES]
    if len(tail_items) >= DELIVERY_TAIL_WIP_LIMIT:
        add_alarm(
            5,
            f"🚦 交付尾部已有 {len(tail_items)} 篇，达到或超过 WIP 上限 {DELIVERY_TAIL_WIP_LIMIT} 篇"
            " → 暂停激活上游内容，先完成标题、审稿和发布",
        )

    for item in todo_items + in_progress_items:
        stagnant = days_since(item["updated"])
        if stagnant is None:
            continue
        title = item["title"]
        stage = item["stage"]
        priority = item["priority"]
        # 每篇内容只产生一个主告警。越接近发布，越优先给出推进动作，
        # 不再同时出现“继续 / 弃用 / 起标题”等互相冲突的建议。
        if stage == "reviewed" and stagnant > 1:
            add_alarm(10, f"🚀 《{title}》已通过质检 {stagnant} 天 → 确认平台后发布归档")
        elif stage == "titled" and stagnant > 1:
            add_alarm(11, f"⚡ 《{title}》标题已定 {stagnant} 天 → 说“审稿：{title}”完成发布前质检")
        elif stage == "drafted" and stagnant > 1:
            add_alarm(12, f"⚡ 《{title}》初稿完成 {stagnant} 天 → 说“标题：{title}”生成标题候选")
        elif stage == "assets_ready" and stagnant > 2:
            add_alarm(13, f"⚡ 《{title}》素材已确认 {stagnant} 天 → 说“写：{title}”开始写作")
        elif stage == "planned" and stagnant > 2:
            add_alarm(40, f"⚡ 《{title}》大纲已定 {stagnant} 天，还没确认素材支撑 → 说“确认素材：{title}”继续")
        elif stage == "checked_in" and stagnant > 7:
            add_alarm(50, f"⚠️ 《{title}》入库 {stagnant} 天未策划 → 说“策划：{title}”继续，或复评后弃用")
        elif priority == "S" and stagnant > 3:
            add_alarm(60, f"🔥 S级《{title}》停滞 {stagnant} 天 → 说“继续”推进，或复评后弃用")
        elif priority == "A" and stagnant > 7:
            add_alarm(61, f"⚠️ A级《{title}》停滞 {stagnant} 天 → 说“继续”推进，或复评后弃用")
        elif stagnant > 14:
            add_alarm(62, f"🗑️ 《{title}》超过 14 天未更新 → 先复评价值，再决定继续或弃用")

    old_inbox = [item for item in inbox_items if (days_since(item["created"]) or 0) > 1]
    if old_inbox:
        add_alarm(50, f"📥 选题 inbox 有 {len(old_inbox)} 篇素材超过 24 小时未处理 → 说“帮我整理inbox”")

    old_material_inbox = [item for item in material_inbox_items if (days_since(item["created"]) or 0) > 1]
    if old_material_inbox:
        add_alarm(51, f"📦 素材库 inbox 有 {len(old_material_inbox)} 篇资产超过 24 小时未整理 → 说“帮我整理inbox”")

    published_with_data = []
    for item in published_items:
        item_text = read_text(item["path"])
        if "**数据填写状态**：已填写" in item_text or "**数据填写状态**: 已填写" in item_text:
            published_with_data.append(item)

    if latest_review_date:
        new_data_count = sum(
            1
            for item in published_with_data
            if parse_date(item.get("published_date", ""))
            and parse_date(item.get("published_date", "")) > latest_review_date
        )
        if new_data_count >= 3:
            add_alarm(60, f"📊 上次复盘后新增 {new_data_count} 篇有效数据 → 说“复盘”查看数据")
    elif len(published_with_data) >= 3:
        add_alarm(61, f"📊 已有 {len(published_with_data)} 篇有效数据，建议做首次复盘 → 说“复盘”建立数据基线")

    for item in published_items:
        published = parse_date(item.get("published_date", ""))
        if not published or (today - published).days <= 3:
            continue
        text = read_text(item["path"])
        if "**数据填写状态**：未填写" in text or "**数据填写状态**: 未填写" in text:
            add_alarm(70, f"📝 《{item['title']}》发布 {(today - published).days} 天未填数据 → 说“填数据”补录")

    alarms = [message for _, message in sorted(alarms, key=lambda item: (item[0], item[1]))]

    suggestion = compute_suggestion(in_progress_items, todo_items, inbox_items, material_inbox_items, alarms)
    inbox_stage_counts = Counter(item["stage"] or "raw_idea" for item in inbox_items)
    material_inbox_counts = Counter(item["bucket"] or "未分类" for item in material_inbox_items)

    lines = []
    if ongoing_task:
        lines.extend(
            [
                "🔄 上次中断的任务",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                f"· {ongoing_task}",
                "",
            ]
        )

    lines.extend(
        [
            "📊 工作区状态",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📈 流程健康度",
            f"  · 平均完成周期: {str(avg_completion) + '天' if avg_completion is not None else '数据不足'} (raw_idea → published)",
            f"  · 当前在途: {len(all_active)}篇内容 | 素材待整理: {len(material_inbox_items)}篇 | 本月已完成: {month_done}篇",
            f"  · 流程效率: {efficiency} — 基于平均停滞时长",
            f"  · 最大瓶颈: {bottleneck}",
            f"  · 交付尾部 WIP: {len(tail_items)} / {DELIVERY_TAIL_WIP_LIMIT}篇",
            f"  · 记忆护栏: 已否决方向 {rejected_count} 条 | 待验证假设 {hypothesis_count} 条",
            "",
        ]
    )

    if alarms:
        lines.append("⚠️ 告警")
        for alarm in alarms:
            lines.append(f"  · {alarm}")
        lines.append("")

    lines.append(f"🔴 进行中 ({len(in_progress_items)}篇)")
    if in_progress_items:
        for item in in_progress_items:
            stagnant = days_since(item["updated"])
            lines.append(
                f"  · {item['title']} — stage: {item['stage']} — 停滞: {stagnant if stagnant is not None else '-'}天 — 下一步: {compute_next_action(item['stage'], item['title'])}"
            )
    else:
        lines.append("  · 无")
    lines.append("")

    lines.append(f"🟡 待写 ({len(todo_items)}篇)")
    if todo_items:
        for item in todo_items:
            stagnant = days_since(item["updated"])
            priority = item["priority"] or "-"
            lines.append(
                f"  · [{priority}] {item['title']} — stage: {item['stage']} — 停滞: {stagnant if stagnant is not None else '-'}天"
            )
    else:
        lines.append("  · 无")
    lines.append("")

    lines.append(f"📥 选题 Inbox ({len(inbox_items)}篇待处理)")
    if inbox_items:
        parts = [f"{stage}: {count}篇" for stage, count in sorted(inbox_stage_counts.items())]
        lines.append(f"  · {' | '.join(parts)}")
    else:
        lines.append("  · raw_idea: 0篇")
    lines.append("")

    lines.append(f"📦 素材 Inbox ({len(material_inbox_items)}篇待整理)")
    if material_inbox_items:
        parts = [f"{bucket}: {count}篇" for bucket, count in sorted(material_inbox_counts.items())]
        lines.append(f"  · {' | '.join(parts)}")
    else:
        lines.append("  · 无")
    lines.append("")

    lines.extend(
        [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"💡 建议: {suggestion}",
            "",
            *QUICK_COMMAND_LINES,
        ]
    )

    return "\n".join(lines)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(build_dashboard())
