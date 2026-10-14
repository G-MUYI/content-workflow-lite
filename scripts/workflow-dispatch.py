#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from workflow_config import (
    CONTENT_ROOT,
    DEFAULT_WORKFLOW_MODE,
    DELIVERY_TAIL_STAGES,
    DELIVERY_TAIL_WIP_LIMIT,
    MATERIAL_ROOT,
    NEXT_ACTION_STAGE_ORDER,
    ROOT,
    ROUTE_RULES,
    WORKFLOW_MODES,
)
from workflow_lib import parse_frontmatter_document, read_text, scalar_text


@dataclass
class WorkflowFile:
    path: Path
    title: str
    stage: str
    priority: str
    updated: str
    content_form: str
    recommended_path: str
    workflow_mode: str


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


def extract_section(text: str, heading: str, level: int = 2) -> str:
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


def extract_subsection(text: str, parent: str, child: str) -> str:
    parent_section = extract_section(text, parent, 2)
    if not parent_section:
        return ""
    return extract_section(parent_section, child, 3)


def extract_frontmatter_block(text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    return match.group(1) if match else ""


def value_has_real_content(value: str) -> bool:
    value = re.sub(r"<!--.*?-->", "", str(value or ""), flags=re.S).strip()
    value = value.strip("|").strip()
    if not value:
        return False
    placeholders = [
        "（待",
        "(待",
        "待补充",
        "待后续",
        "待选题",
        "待策划",
        "待写",
        "待填写",
        "待确认",
        "xxx",
        "XXX",
        "[]",
        "是 / 否",
        "像 / 不像",
    ]
    if any(token in value for token in placeholders):
        return False
    if re.fullmatch(r"[（(][^）)]*[）)]", value):
        return False
    if re.fullmatch(r"[-|:：/\s\d.]+", value):
        return False
    return True


def table_value(section: str, label: str) -> str:
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) >= 2 and label in cells[0]:
            return cells[1]
    return ""


def missing_table_values(section: str, labels: list[str]) -> list[str]:
    return [label for label in labels if not value_has_real_content(table_value(section, label))]


def checked_box_count(section: str) -> int:
    return len(re.findall(r"^\s*-\s*\[[xX]\]", section, re.M))


def has_nonempty_yaml_sequence(text: str, key: str) -> bool:
    lines = extract_frontmatter_block(text).splitlines()
    for index, line in enumerate(lines):
        if not re.match(rf"^{re.escape(key)}\s*:", line):
            continue
        _, raw_value = line.split(":", 1)
        inline_value = raw_value.strip()
        if inline_value:
            if inline_value in {"[]", "null", "None"}:
                return False
            if inline_value.startswith("[") and inline_value.endswith("]"):
                return value_has_real_content(inline_value.strip("[]"))
            return value_has_real_content(inline_value)
        for child in lines[index + 1 :]:
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*:", child):
                break
            stripped = child.strip()
            if stripped.startswith("- ") and value_has_real_content(stripped[2:]):
                return True
        return False
    return False


def strip_quotes(value: str) -> str:
    value = str(value or "").strip()
    if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
        return value[1:-1]
    return value


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = read_text(path)
    document = parse_frontmatter_document(text)
    if not document:
        return {}
    return {key: scalar_text(value) for key, value in document.data.items()}


def parse_date(value: str) -> date | None:
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", strip_quotes(value))
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def days_since(value: str) -> int | None:
    target = parse_date(value)
    if not target:
        return None
    return (date.today() - target).days


def match_route(command: str) -> dict | None:
    command = command.strip()
    if not command:
        return None

    candidates = [
        (trigger, route)
        for route in ROUTE_RULES
        for trigger in route["triggers"]
    ]
    for trigger, route in sorted(candidates, key=lambda item: len(item[0]), reverse=True):
        if (
            command == trigger
            or command.startswith(f"{trigger}：")
            or command.startswith(f"{trigger}:")
            or command.startswith(f"{trigger} ")
        ):
            return route
    return None


def active_markdown_files() -> list[Path]:
    roots = [
        CONTENT_ROOT / "进行中",
        CONTENT_ROOT / "待写",
        CONTENT_ROOT / "_inbox",
    ]
    files = []
    for root in roots:
        if root.exists():
            files.extend(sorted(path for path in root.glob("*.md") if path.is_file()))
    return files


def workflow_file(path: Path) -> WorkflowFile:
    frontmatter = parse_frontmatter(path)
    return WorkflowFile(
        path=path,
        title=frontmatter.get("title") or path.stem,
        stage=frontmatter.get("stage", ""),
        priority=frontmatter.get("priority", ""),
        updated=frontmatter.get("updated", ""),
        content_form=frontmatter.get("content_form", ""),
        recommended_path=frontmatter.get("recommended_path", ""),
        workflow_mode=frontmatter.get("workflow_mode", ""),
    )


def priority_rank(priority: str) -> int:
    return {"S": 0, "A": 1, "B": 2, "C": 3}.get(priority, 9)


def stage_rank(stage: str) -> int:
    try:
        return NEXT_ACTION_STAGE_ORDER.index(stage)
    except ValueError:
        return 99


def active_workflow_files() -> list[WorkflowFile]:
    items = [workflow_file(path) for path in active_markdown_files()]
    return sorted(
        items,
        key=lambda item: (
            stage_rank(item.stage),
            priority_rank(item.priority),
            -(days_since(item.updated) or 0),
            item.path.name,
        ),
    )


def effective_workflow_mode(item: WorkflowFile) -> str:
    if item.workflow_mode in WORKFLOW_MODES:
        return item.workflow_mode
    if item.content_form == "short_post" or item.recommended_path == "short_post_first":
        return "quick"
    return DEFAULT_WORKFLOW_MODE


def short_post_allowed(item: WorkflowFile) -> bool:
    return effective_workflow_mode(item) == "quick"


def title_candidates_ready(item: WorkflowFile) -> bool:
    text = read_text(item.path)
    title_section = extract_section(text, "标题备选", 2)
    formula_ids = set(re.findall(r"XHS-\d{3}", title_section.upper()))
    # This only detects candidates to evaluate, never a completed title selection.
    return bool(formula_ids)


def style_gate_gaps(item: WorkflowFile) -> list[str]:
    text = read_text(item.path)
    gaps: list[str] = []
    workflow_mode = effective_workflow_mode(item)

    if workflow_mode == "flagship":
        style_translation = extract_subsection(text, "内容策划", "风格转译")
        missing_style = missing_table_values(
            style_translation,
            ["调性档位", "适合本人风格的开头", "可用口语表达", "作者在场设计", "本篇禁用表达", "正文语气基准", "人格姿态自检"],
        )
        if missing_style:
            gaps.append("风格转译未填完整")

        author_presence = table_value(style_translation, "作者在场设计")
        if value_has_real_content(author_presence) and any(
            label not in author_presence
            for label in ["正文候选", "验证边界", "内部过程日志"]
        ):
            gaps.append("作者在场设计未完成三类分流")

        if checked_box_count(extract_subsection(text, "内容策划", "反AI味检查")) < 6:
            gaps.append("反AI味检查未全部勾选")

    style_self_check = extract_subsection(text, "写作笔记", "风格自检")
    if not style_self_check:
        gaps.append("风格自检缺失")
    else:
        if not re.search(r"风格档案是否已读取[：:]\s*是", style_self_check):
            gaps.append("风格自检未确认已读取风格档案")
        if not re.search(r"自检结论[：:]\s*像(?!\s*/\s*不像)", style_self_check):
            gaps.append("风格自检未通过")

    return gaps


def build_action(item: WorkflowFile) -> dict[str, object]:
    file_path = to_posix(item.path)
    tutorial_path = item.recommended_path == "tutorial"
    base = {
        "file": file_path,
        "title": item.title,
        "stage": item.stage,
        "priority": item.priority,
        "fallback_stage": item.stage,
    }

    if item.stage in {"drafted", "titled"}:
        gaps = style_gate_gaps(item)
        if gaps:
            return {
                **base,
                "skill": "story-writer",
                "command": f"补风格链路：{item.title}",
                "next_stage": item.stage,
                "target_stage": item.stage,
                "blocked": False,
                "reason": "先按写手规则修复风格链路，再继续原任务："
                + "、".join(gaps),
                "completion_condition": "实际修复并复核风格缺口，保持当前合法 stage，不伪造自检",
            }

    actions = {
        "raw_idea": {
            "skill": "topic-master",
            "command": f"整理选题inbox：{item.title}",
            "next_stage": "topics_generated",
            "target_stage": "topics_generated",
            "blocked": False,
            "reason": "原始素材需要先生成候选选题。",
            "completion_condition": "候选选题已写入且实际 stage=topics_generated",
        },
        "topics_generated": {
            "skill": "topic-master",
            "command": f"确认入库：{item.title}",
            "next_stage": "checked_in",
            "target_stage": "checked_in",
            "blocked": False,
            "reason": "复用候选，在授权目标内选定主推角度；用户明确保留终选权时等待。",
            "completion_condition": "实际选定角度并保存 Brief 与选择依据后 stage=checked_in",
        },
        "market_researched": {
            "skill": "viral-content-strategist",
            "command": f"策划：{item.title}",
            "next_stage": "strategies_generated",
            "target_stage": "strategies_generated",
            "blocked": False,
            "reason": "市场调研已完成，可以进入内容策划。",
            "completion_condition": "策划草案已写入且实际 stage=strategies_generated",
        },
        "strategies_generated": {
            "skill": "viral-content-strategist",
            "command": f"确认大纲：{item.title}",
            "next_stage": "planned",
            "target_stage": "planned",
            "blocked": False,
            "reason": "核验正式大纲和派活清单，在授权目标内完成定稿。",
            "completion_condition": "大纲选择落实且适用门禁通过后实际 stage=planned",
        },
        "planned": {
            "skill": "viral-content-strategist",
            "command": f"确认素材：{item.title}",
            "next_stage": "planned",
            "target_stage": "assets_ready",
            "blocked": False,
            "reason": (
                "先核验实测任务包；用已授权工具补齐至少 3 张关键截图或等价证据及实际结论。关键证据未取得时保持 planned，仅请求不能自行取得的输入。"
                if tutorial_path
                else "先核验并补齐截图/案例/提示词/数据和 Hook 证据；缺口未解决时保持 planned，不用口头确认代替证据。"
            ),
            "completion_condition": "可信支撑通过门禁后实际 stage=assets_ready",
        },
        "assets_ready": {
            "skill": "story-writer",
            "command": f"写：{item.title}",
            "next_stage": "drafted",
            "target_stage": "drafted",
            "blocked": False,
            "reason": "素材支撑已确认，可以开始写正文。",
            "completion_condition": "正文与风格自检已保存且实际 stage=drafted",
        },
        "drafted": {
            "skill": "title-master",
            "command": f"标题：{item.title}",
            "next_stage": "drafted",
            "target_stage": "titled",
            "blocked": False,
            "reason": "生成候选并按任务完成终选；仅有候选或用户保留终选权时保持 drafted。",
            "completion_condition": "候选与发布包已保存；仅有候选保持 drafted，终选及证据映射落实后 stage=titled",
        },
        "titled": {
            "skill": "content-reviewer",
            "command": f"审稿：{item.title}",
            "next_stage": "reviewed",
            "target_stage": "reviewed",
            "blocked": False,
            "reason": "标题已定，可以做发布前质检；未通过时保持 titled。",
            "completion_condition": "审稿报告已保存；通过则 stage=reviewed，未通过保持 titled",
        },
        "reviewed": {
            "skill": "scripts/publish-content.py",
            "command": f"这篇发了：{item.title}",
            "next_stage": "published",
            "target_stage": "published",
            "blocked": True,
            "reason": "此只读建议没有外部发布授权或已发布事实；结合会话核对平台、日期和真实结果，已有授权不重复询问。",
            "completion_condition": "实际发布已成功或用户报告已发布，按真实平台与日期完成本地归档后 stage=published",
        },
    }

    if item.stage == "checked_in":
        if short_post_allowed(item):
            return {
                **base,
                "skill": "story-writer",
                "command": f"写：{item.title}",
                "next_stage": "drafted",
                "target_stage": "drafted",
                "blocked": False,
                "reason": "速发短篇允许 checked_in 直接进入写作。",
                "completion_condition": "短篇正文与最小实证已保存且实际 stage=drafted",
            }
        return {
            **base,
            "skill": "viral-content-strategist",
            "command": f"策划：{item.title}",
            "next_stage": "strategies_generated",
            "target_stage": "strategies_generated",
            "blocked": False,
            "reason": "按核心承诺判断是否需要市场调研；需要则补充，否则直接策划，不要求用户选择工具路径。",
            "completion_condition": "所需研究与策划完成并保存后按对应合法阶段验收",
        }

    action = actions.get(item.stage)
    if not action:
        return {
            **base,
            "skill": "",
            "command": "",
            "next_stage": "",
            "target_stage": "",
            "blocked": True,
            "reason": f"当前 stage={item.stage or '(空)'} 没有登记下一步。",
            "completion_condition": "无",
        }
    if item.stage == "drafted" and title_candidates_ready(item):
        return {
            **base,
            "skill": "title-master",
            "command": f"确认标题：{item.title}",
            "next_stage": "titled",
            "target_stage": "titled",
            "blocked": False,
            "reason": "复用已有候选，核验承诺并在授权范围内终选；用户保留终选权时等待。",
            "completion_condition": "实际选定标题并记录选择依据、公式与证据映射后 stage=titled",
        }
    return {**base, **action}


def next_action_payload(limit: int = 1, *, target: str = "") -> dict[str, object]:
    items = active_workflow_files()
    tail_items = [item for item in items if item.stage in DELIVERY_TAIL_STAGES]
    wip_limited = not target and len(tail_items) >= DELIVERY_TAIL_WIP_LIMIT
    if target:
        items = [item for item in items if target in {item.title, to_posix(item.path)}]
        if len(items) != 1:
            return {
                "actions": [], "blocked_actions": [], "active_files": [],
                "run_contract": None,
                "selection_error": "指定对象不存在或不唯一；请使用准确标题或项目相对文件路径，不回退到全库自动选取。",
            }
    actions = []
    for item in items:
        action = build_action(item)
        if wip_limited and item.stage not in DELIVERY_TAIL_STAGES:
            action = {
                **action,
                "blocked": True,
                "reason": (
                    f"交付尾部已有 {len(tail_items)} 篇，达到 WIP 上限 "
                    f"{DELIVERY_TAIL_WIP_LIMIT}；先完成 drafted / titled / reviewed。"
                ),
            }
        actions.append(action)
    executable = [action for action in actions if not action["blocked"]]
    blocked = [action for action in actions if action["blocked"]]
    selected = executable[:limit]
    return {
        "actions": selected,
        "blocked_actions": blocked,
        "active_files": [to_posix(item.path) for item in items],
        "run_contract": build_run_contract(selected, blocked),
        "wip_policy": {
            "active": wip_limited,
            "tail_count": len(tail_items),
            "limit": DELIVERY_TAIL_WIP_LIMIT,
        },
    }


def build_run_contract(
    actions: list[dict[str, object]],
    blocked_actions: list[dict[str, object]],
) -> dict[str, object] | None:
    if not actions:
        return None
    return {
        "purpose": "在用户授权目标内推进所选阶段并修复必要前置；actions 不是已完成证明",
        "completion": [
            f"《{action['title']}》验收：{action['completion_condition']}"
            for action in actions
        ],
        "targets": [
            f"《{action['title']}》目标 stage={action['target_stage']}"
            for action in actions
        ],
        "fallbacks": [
            f"《{action['title']}》失败或待确认时保持 stage={action['fallback_stage']}"
            for action in actions
        ],
        "evidence": [
            f"执行后重新读取 {action['file']} 的实际 stage 与对应阶段区块"
            for action in actions
        ]
        + [
            "stage、目录和 status 一致",
            "python scripts/validate-workflow.py 未新增错误",
        ],
        "forbidden": [
            "跳过未登记的 stage",
            "修改校验器、测试或阈值制造通过",
            "用预期结果冒充实测结果",
            "只在对话中声称完成而不保存文件",
        ],
        "scope": [str(action["file"]) for action in actions],
        "tradeoff": "事实准确 > 门禁完整 > 推进速度",
        "unknowns": [
            str(action["reason"])
            for action in blocked_actions[:5]
        ],
    }


def assets_ready_payload(limit: int = 3, *, target: str = "") -> dict[str, object]:
    items = [item for item in active_workflow_files() if item.stage == "planned"]
    if target:
        items = [item for item in items if target in {item.title, to_posix(item.path)}]
        if len(items) != 1:
            return {
                "actions": [], "blocked_actions": [], "active_files": [],
                "selection_error": "指定的 planned 文件不存在或不唯一；请使用准确标题或项目相对文件路径。",
            }
    actions = [build_action(item) for item in items]
    return {
        "actions": actions[:limit],
        "blocked_actions": [],
        "active_files": [to_posix(item.path) for item in items],
    }


def inbox_files() -> list[dict[str, object]]:
    items: list[dict[str, object]] = []

    topic_inbox = CONTENT_ROOT / "_inbox"
    if topic_inbox.exists():
        for path in sorted(topic_inbox.glob("*.md")):
            frontmatter = parse_frontmatter(path)
            stage = frontmatter.get("stage", "raw_idea") or "raw_idea"
            skill = "topic-master"
            command = "确认入库" if stage == "topics_generated" else "整理选题inbox"
            items.append(
                {
                    "file": to_posix(path),
                    "bucket": "选题库",
                    "stage": stage,
                    "skill": skill,
                    "command": f"{command}：{frontmatter.get('title') or path.stem}",
                    "days": days_since(frontmatter.get("created", "")),
                }
            )

    if MATERIAL_ROOT.exists():
        for inbox_dir in sorted(path for path in MATERIAL_ROOT.rglob("_inbox") if path.is_dir()):
            bucket = inbox_dir.parent.name
            for path in sorted(inbox_dir.glob("*.md")):
                frontmatter = parse_frontmatter(path)
                material_type = frontmatter.get("material_type", "")
                is_prompt_asset = bucket == "提示词" or material_type == "prompt_asset"
                skill = "prompt-librarian" if is_prompt_asset else "knowledge-gardener"
                command = "整理提示词" if skill == "prompt-librarian" else "整理素材库"
                content_handoff = frontmatter.get("content_handoff", "pending") or "pending"
                needs_topic_handoff = is_prompt_asset and content_handoff not in {"done", "skipped"}
                items.append(
                    {
                        "file": to_posix(path),
                        "bucket": bucket,
                        "title": frontmatter.get("title") or path.stem,
                        "stage": frontmatter.get("stage", "collected") or "collected",
                        "skill": skill,
                        "command": f"{command}：{frontmatter.get('title') or path.stem}",
                        "topic_handoff": needs_topic_handoff,
                        "topic_command": f"从提示词素材生成选题：{frontmatter.get('title') or path.stem}" if needs_topic_handoff else "",
                        "content_handoff": content_handoff,
                        "days": days_since(frontmatter.get("created", "")),
                    }
                )

    return sorted(items, key=lambda item: (item["days"] is None, -(item["days"] or 0), item["bucket"], item["file"]))


def inbox_payload(skill_filter: str | None = None) -> dict[str, object]:
    all_items = inbox_files()
    items = [item for item in all_items if item["skill"] == skill_filter] if skill_filter else all_items
    return {
        "items": items,
        "actions": items[:3],
        "summary": {
            "total": len(items),
            "topic": len([item for item in items if item["skill"] == "topic-master"]),
            "prompt": len([item for item in items if item["skill"] == "prompt-librarian"]),
            "material": len([item for item in items if item["skill"] == "knowledge-gardener"]),
            "topic_handoff": len([item for item in items if item.get("topic_handoff")]),
        },
    }


def build_payload(command: str, route: dict | None) -> dict[str, object]:
    payload: dict[str, object] = {
        "command": command,
        "matched": bool(route),
        "route": route,
        "active_files": [to_posix(path) for path in active_markdown_files()],
    }

    if not route:
        return payload

    intent = route["intent"]
    target = ""
    for trigger in sorted(route["triggers"], key=len, reverse=True):
        if command.startswith(trigger) and command[len(trigger):len(trigger) + 1] in {"：", ":", " "}:
            target = command[len(trigger):].lstrip("：: ").strip()
            break
    if intent == "继续推进":
        payload["dispatch"] = next_action_payload(limit=1, target=target)
    elif intent == "一键推进":
        payload["dispatch"] = next_action_payload(limit=3, target=target)
    elif intent == "素材准备确认":
        payload["dispatch"] = assets_ready_payload(limit=3, target=target)
    elif intent == "全库 inbox 批量处理":
        payload["dispatch"] = inbox_payload()
    elif intent == "整理提示词资产":
        payload["dispatch"] = inbox_payload(skill_filter="prompt-librarian")
    return payload


def print_action(action: dict[str, object]) -> None:
    print(f"  · 《{action['title']}》")
    print(f"    文件: {action['file']}")
    print(f"    当前 stage: {action['stage']}")
    print(f"    目标 stage: {action.get('target_stage', action['next_stage'])}")
    print(f"    调用: {action['skill']}")
    print(f"    命令: {action['command']}")
    print(f"    原因: {action['reason']}")
    print(f"    验收: {action.get('completion_condition', '执行后读取实际状态')}")


def print_inbox_item(item: dict[str, object]) -> None:
    days = item["days"] if item["days"] is not None else "-"
    print(f"  · {item['bucket']} | {item['stage']} | 停留 {days} 天")
    print(f"    文件: {item['file']}")
    print(f"    调用: {item['skill']}")
    print(f"    命令: {item['command']}")
    if item.get("topic_handoff"):
        print("    同步转交: topic-master")
        print(f"    选题命令: {item['topic_command']}")


def print_text_report(payload: dict[str, object]) -> None:
    route = payload["route"]
    print("工作流命令路由")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if not route:
        print(f"- 命令: {payload['command'] or '(空)'}")
        print("- 匹配: 未找到")
        print("可用命令：")
        for item in ROUTE_RULES:
            print(f"  · {' / '.join(item['triggers'])} → {item['target']}")
        return

    print(f"- 命令: {payload['command']}")
    print(f"- 意图: {route['intent']}")
    print(f"- 目标: {route['target']}")
    print(f"- 前置检查: {route['preflight']}")

    dispatch = payload.get("dispatch")
    if dispatch and dispatch.get("selection_error"):
        print(f"- 对象选择: {dispatch['selection_error']}")
        return
    if not dispatch:
        active_files = payload["active_files"]
        if active_files:
            print("- 当前活动文件:")
            for item in active_files:
                print(f"  · {item}")
        else:
            print("- 当前活动文件: 无")
        return

    print("")
    if route["intent"] in {"全库 inbox 批量处理", "整理提示词资产"}:
        summary = dispatch["summary"]
        print("分流结果")
        print(f"- 待处理: {summary['total']} 个 | 选题: {summary['topic']} | 提示词: {summary['prompt']} | 素材: {summary['material']} | 选题转交: {summary['topic_handoff']}")
        if dispatch["actions"]:
            print("- 建议优先处理:")
            for item in dispatch["actions"]:
                print_inbox_item(item)
        else:
            print("- 当前没有 inbox 文件")
        return

    actions = dispatch["actions"]
    blocked = dispatch["blocked_actions"]
    wip_policy = dispatch.get("wip_policy")
    if wip_policy and wip_policy["active"]:
        print(
            f"交付尾部 WIP: {wip_policy['tail_count']} / {wip_policy['limit']}，"
            "已暂停自动激活上游内容"
        )
        print("")
    if actions:
        print("可执行下一步")
        for action in actions:
            print_action(action)
        contract = dispatch.get("run_contract")
        if contract:
            print("")
            print("本轮自动推进合同")
            print(f"- 目的: {contract['purpose']}")
            print(f"- 取舍: {contract['tradeoff']}")
            print(f"- 范围: {', '.join(contract['scope'])}")
            print("- 目标态:")
            for item in contract["targets"]:
                print(f"  · {item}")
            print("- 完成验收:")
            for item in contract["completion"]:
                print(f"  · {item}")
            print("- 失败保持态:")
            for item in contract["fallbacks"]:
                print(f"  · {item}")
            print("- 禁止假完成:")
            for item in contract["forbidden"]:
                print(f"  · {item}")
    else:
        print("可执行下一步: 无")

    if blocked:
        print("")
        print("需要用户确认/补信息")
        for action in blocked[:5]:
            print_action(action)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if has_flag("--routes"):
        print("工作流命令路由")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for item in ROUTE_RULES:
            print(f"- {' / '.join(item['triggers'])} → {item['target']}")
            print(f"  前置检查: {item['preflight']}")
        return

    command = read_arg("--command") or " ".join(arg for arg in sys.argv[1:] if not arg.startswith("--"))
    route = match_route(command)
    payload = build_payload(command, route)

    if has_flag("--json"):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print_text_report(payload)


if __name__ == "__main__":
    main()
