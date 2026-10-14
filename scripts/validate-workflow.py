#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from workflow_config import (
    ASSET_CORE_KEYS,
    CONTENT_CORE_KEYS,
    CONTENT_DIR_STAGES,
    CONTENT_EXTENDED_KEYS,
    CONTENT_GROWTH_BRIEF_KEYS,
    CONTENT_ROOT,
    CONTENT_STAGE_STATUS,
    CONTENT_UNIT_TYPES,
    DEFAULT_WORKFLOW_MODE,
    KNOWN_SKILLS,
    MATERIAL_ROOT,
    ROOT,
    WORKFLOW_MODES,
)
from workflow_lib import parse_frontmatter_document, read_text, scalar_text


OPENING_DIVERSITY_RULE_DATE = "2026-08-31"


@dataclass
class Finding:
    level: str
    code: str
    path: str
    message: str


def has_flag(name: str) -> bool:
    return name in sys.argv


def to_posix(path: Path | None) -> str:
    if path is None:
        return ""
    return path.relative_to(ROOT).as_posix()


def parse_scalar(raw_value: str) -> str:
    value = raw_value.split("#", 1)[0].strip()
    if not value:
        return ""
    if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict[str, str] | None:
    document = parse_frontmatter_document(text)
    if not document:
        return None
    return {key: scalar_text(value) for key, value in document.data.items()}


def walk_markdown_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.md") if path.is_file())


def has_section(text: str, heading: str) -> bool:
    return bool(re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.M))


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


def section_has_real_content(content: str) -> bool:
    if not content:
        return False
    cleaned = re.sub(r"<!--.*?-->", "", content, flags=re.S).strip()
    placeholders = [
        "（",
        "(待",
        "待补充",
        "待后续",
        "| |",
        "|  |",
        "- ：",
        "- :",
    ]
    if not cleaned:
        return False
    non_empty_lines = [
        line.strip()
        for line in cleaned.splitlines()
        if line.strip() and not re.match(r"^\|?\s*-{2,}", line.strip())
    ]
    meaningful = [
        line
        for line in non_empty_lines
        if not any(token in line for token in placeholders)
        and not re.fullmatch(r"[-|:\s\d.]+", line)
        and not re.fullmatch(r"[#>\-\s]*", line)
    ]
    return bool(meaningful)


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
        "missing / partial / ready",
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
    missing = []
    for label in labels:
        if not value_has_real_content(table_value(section, label)):
            missing.append(label)
    return missing


def checked_box_count(section: str) -> int:
    return len(re.findall(r"^\s*-\s*\[[xX]\]", section, re.M))


def has_nonempty_yaml_sequence(text: str, key: str) -> bool:
    frontmatter = extract_frontmatter_block(text)
    lines = frontmatter.splitlines()
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


def report(findings: list[Finding], level: str, code: str, path: Path | None, message: str) -> None:
    findings.append(Finding(level, code, to_posix(path), message))


def content_workflow_mode(frontmatter: dict[str, str], text: str) -> str:
    explicit = frontmatter.get("workflow_mode", "")
    if explicit in WORKFLOW_MODES:
        return explicit
    if (
        frontmatter.get("content_form") == "short_post"
        or frontmatter.get("recommended_path") == "short_post_first"
        or "速发短篇模式" in text
        or "快速出稿模式" in text
    ):
        return "quick"
    return DEFAULT_WORKFLOW_MODE


def validate_style_chain(
    path: Path,
    text: str,
    frontmatter: dict[str, str],
    findings: list[Finding],
    active: bool,
    workflow_mode: str,
) -> None:
    stage = frontmatter.get("stage", "")
    stage_order = list(CONTENT_STAGE_STATUS.keys())
    stage_index = stage_order.index(stage) if stage in stage_order else -1
    if stage_index < 0:
        return

    if stage_index >= stage_order.index("strategies_generated") and workflow_mode == "flagship":
        style_translation = extract_subsection(text, "内容策划", "风格转译")
        required_style_labels = [
            "调性档位",
            "适合本人风格的开头",
            "可用口语表达",
            "作者在场设计",
            "本篇禁用表达",
            "正文语气基准",
            "人格姿态自检",
        ]
        if frontmatter.get("created", "") >= OPENING_DIVERSITY_RULE_DATE:
            required_style_labels.extend(["开头候选", "近5篇撞型检查"])
        missing_style = missing_table_values(
            style_translation,
            required_style_labels,
        )
        if missing_style:
            report(
                findings,
                "error" if active else "warn",
                "content.style_translation_incomplete",
                path,
                "风格转译未填完整："
                + ", ".join(missing_style),
            )

        author_presence = table_value(style_translation, "作者在场设计")
        missing_presence_parts = [
            label
            for label in ["正文候选", "验证边界", "内部过程日志"]
            if label not in author_presence
        ]
        if value_has_real_content(author_presence) and missing_presence_parts:
            report(
                findings,
                "error" if active else "warn",
                "content.author_presence_routing_incomplete",
                path,
                "作者在场设计需要完成三类分流："
                + ", ".join(missing_presence_parts),
            )

        anti_ai = extract_subsection(text, "内容策划", "反AI味检查")
        checked_count = checked_box_count(anti_ai)
        if checked_count < 6:
            report(
                findings,
                "error" if active else "warn",
                "content.anti_ai_check_incomplete",
                path,
                f"反AI味检查需要 6 条全部勾选，当前检测到 {checked_count} 条",
            )

    if stage_index >= stage_order.index("drafted"):
        style_self_check = extract_subsection(text, "写作笔记", "风格自检")
        if not section_has_real_content(style_self_check):
            report(
                findings,
                "error" if active else "warn",
                "content.style_self_check_missing",
                path,
                "drafted 及之后需要完成：## 写作笔记 > ### 风格自检",
            )
            return

        if not re.search(r"风格档案是否已读取[：:]\s*是", style_self_check):
            report(
                findings,
                "error" if active else "warn",
                "content.style_profile_not_read",
                path,
                "风格自检必须明确记录：风格档案是否已读取：是",
            )
        if not re.search(r"自检结论[：:]\s*像(?!\s*/\s*不像)", style_self_check):
            report(
                findings,
                "error" if active else "warn",
                "content.style_self_check_not_passed",
                path,
                "风格自检必须明确记录：自检结论：像",
            )


def validate_opening_diversity(
    path: Path,
    text: str,
    frontmatter: dict[str, str],
    findings: list[Finding],
    active: bool,
) -> None:
    stage = frontmatter.get("stage", "")
    if stage not in CONTENT_STAGE_STATUS:
        return
    stage_order = list(CONTENT_STAGE_STATUS.keys())
    if stage_order.index(stage) < stage_order.index("drafted"):
        return
    if frontmatter.get("created", "") < OPENING_DIVERSITY_RULE_DATE:
        return

    level = "error" if active else "warn"
    body = extract_section(text, "正文", 2)
    opening = re.sub(r"\s+", " ", body[:500])
    banned_patterns = [
        (
            r"(?:今天|最近|前两天)?\s*(?:在)?\s*整理(?:我的)?素材(?:的)?(?:时候|时)",
            "开头不得把整理素材当作正文事件",
        ),
        (
            r"真正让我停下来看的.{0,100}(?:是|，是).{0,100}(?:差别|区别)",
            "开头不得使用“真正让我停下来看的，是……的差别/区别”固定判断壳",
        ),
    ]
    for pattern, message in banned_patterns:
        if re.search(pattern, opening):
            report(
                findings,
                level,
                "content.opening_formula_banned",
                path,
                message,
            )

    style_self_check = extract_subsection(text, "写作笔记", "风格自检")
    if not re.search(r"开头原型[：:]\s*\S+", style_self_check):
        report(
            findings,
            level,
            "content.opening_archetype_missing",
            path,
            "新稿风格自检必须记录开头原型",
        )
    if not re.search(r"近\s*5\s*篇撞型检查[：:]\s*通过", style_self_check):
        report(
            findings,
            level,
            "content.opening_collision_check_missing",
            path,
            "新稿风格自检必须记录：近 5 篇撞型检查：通过",
        )


def top_content_dir(path: Path) -> str:
    relative = to_posix(path)
    parts = relative.split("/")
    return parts[1] if len(parts) > 1 else ""


def is_short_post_path(frontmatter: dict[str, str], text: str) -> bool:
    return content_workflow_mode(frontmatter, text) == "quick"


def is_tutorial_content(frontmatter: dict[str, str], text: str) -> bool:
    return (
        frontmatter.get("recommended_path", "").strip().lower() == "tutorial"
        or frontmatter.get("content_angle", "").strip().lower() == "tutorial"
        or "教程清单型" in extract_subsection(text, "内容策划", "文章原型")
    )


def labeled_list_value(section: str, label: str) -> str:
    pattern = re.compile(rf"^[ \t]*-[ \t]*{re.escape(label)}[：:][ \t]*([^\r\n]*)$", re.M)
    match = pattern.search(section)
    return match.group(1).strip() if match else ""


def fenced_prompt_blocks(section: str) -> list[str]:
    return [
        match.strip()
        for match in re.findall(r"```(?:text|prompt|markdown)?\s*\n(.*?)\n```", section, re.S | re.I)
        if match.strip()
    ]


def validate_hook_evidence_supplement(
    path: Path,
    text: str,
    findings: list[Finding],
    active: bool,
    stage: str,
    workflow_mode: str,
) -> None:
    if workflow_mode == "quick" or stage not in CONTENT_STAGE_STATUS:
        return

    stage_order = list(CONTENT_STAGE_STATUS.keys())
    stage_index = stage_order.index(stage)
    if stage_index < stage_order.index("strategies_generated"):
        return

    section = extract_subsection(text, "内容策划", "Hook素材增补")
    level = "error" if active else "warn"
    prewriting_stages = {"strategies_generated", "planned", "assets_ready"}
    if not section_has_real_content(section):
        if stage in prewriting_stages:
            report(
                findings,
                level,
                "content.hook_supplement_missing",
                path,
                "非速发内容在策划阶段必须完成：## 内容策划 > ### Hook素材增补",
            )
        return

    mode = labeled_list_value(section, "Hook模式").strip().lower()
    goal = labeled_list_value(section, "Hook目标")
    state = labeled_list_value(section, "Hook可用状态").strip().lower()
    boundary = labeled_list_value(section, "事实边界")

    if stage in prewriting_stages:
        if mode not in {"evidence", "opinion", "hybrid"}:
            report(
                findings,
                level,
                "content.hook_mode_invalid",
                path,
                "Hook模式必须明确为 evidence / opinion / hybrid 中的一种",
            )
        if not value_has_real_content(goal):
            report(
                findings,
                level,
                "content.hook_goal_missing",
                path,
                "Hook素材增补必须写清 Hook目标",
            )
        if not value_has_real_content(boundary):
            report(
                findings,
                level,
                "content.hook_boundary_missing",
                path,
                "Hook素材增补必须写清事实边界",
            )

    if stage_index < stage_order.index("assets_ready"):
        return

    if state != "ready":
        report(
            findings,
            level,
            "content.hook_not_ready",
            path,
            "进入 assets_ready 前必须记录：Hook可用状态：ready",
        )
    if mode in {"evidence", "hybrid"} and not re.search(
        r"\|\s*verified\s*\|", section, re.I
    ):
        report(
            findings,
            level,
            "content.hook_verified_anchor_missing",
            path,
            "evidence / hybrid Hook 进入 assets_ready 前至少需要 1 条 verified 锚点",
        )


def validate_tutorial_test_package(
    path: Path,
    text: str,
    frontmatter: dict[str, str],
    findings: list[Finding],
    active: bool,
    stage_index: int,
) -> None:
    stage_order = list(CONTENT_STAGE_STATUS.keys())
    if stage_index < stage_order.index("strategies_generated"):
        return

    package = extract_subsection(text, "内容策划", "实测任务包")
    level = "error" if active else "warn"
    if not section_has_real_content(package):
        report(findings, level, "content.tutorial_test_package_missing", path, "教程类需要完成：## 内容策划 > ### 实测任务包")
        return

    medium = labeled_list_value(package, "测试媒介")
    goal = labeled_list_value(package, "测试目标")
    if not value_has_real_content(medium):
        report(findings, level, "content.tutorial_medium_missing", path, "实测任务包必须明确测试媒介：AI 绘图 / AI 视频 / AI 编程 / AI 写作 / 其他工具")
    if not value_has_real_content(goal):
        report(findings, level, "content.tutorial_goal_missing", path, "实测任务包必须填写只包含一个主变量的测试目标")

    required_headings = ["输入素材", "可复制测试提示词", "参数与变量", "预期结果与失败信号", "截图清单", "实测结果记录"]
    missing_headings = [heading for heading in required_headings if not extract_section(package, heading, 4)]
    if missing_headings:
        report(
            findings,
            level,
            "content.tutorial_package_sections_missing",
            path,
            f"实测任务包缺少区块：{', '.join(missing_headings)}",
        )

    prompt_blocks = fenced_prompt_blocks(extract_section(package, "可复制测试提示词", 4))
    usable_prompts = [
        prompt
        for prompt in prompt_blocks
        if len(prompt) >= 40 and not re.search(r"待补充|待填写|替换成|占位符", prompt)
    ]
    if not usable_prompts:
        report(findings, level, "content.tutorial_prompt_missing", path, "教程类必须提供至少一条可直接复制测试的完整提示词代码块")

    prompt_text = "\n".join(usable_prompts)
    if re.search(r"AI\s*绘图|图像|image", medium, re.I):
        missing_image_fields = [field for field in ("主体", "场景", "构图", "比例", "禁止") if field not in prompt_text]
        if missing_image_fields:
            report(
                findings,
                level,
                "content.tutorial_image_prompt_incomplete",
                path,
                f"AI 绘图提示词缺少：{', '.join(missing_image_fields)}",
            )
    if re.search(r"AI\s*视频|video", medium, re.I):
        missing_video_fields = [field for field in ("主体", "动作", "镜头", "时长", "比例", "禁止") if field not in prompt_text]
        if missing_video_fields:
            report(
                findings,
                level,
                "content.tutorial_video_prompt_incomplete",
                path,
                f"AI 视频提示词缺少：{', '.join(missing_video_fields)}",
            )

    screenshot_section = extract_section(package, "截图清单", 4)
    screenshot_tasks = re.findall(r"^[ \t]*-[ \t]*\[[ xX]\][ \t]*([^\n]*)", screenshot_section, re.M)
    # A single recording can cover several steps. Check for a concrete plan,
    # not an arbitrary image count or prescribed vocabulary. The executing
    # Agent verifies coverage and actual evidence before advancing the stage.
    if not any(value_has_real_content(task) for task in screenshot_tasks):
        report(
            findings,
            level,
            "content.tutorial_screenshot_plan_incomplete",
            path,
            "教程类需要可执行的截图或等价证据采集项，说明采集位置与证明目的；由执行者核验关键输入、操作条件和结果的覆盖，不固定要求 7 个位置",
        )

    if stage_index < stage_order.index("assets_ready"):
        return

    if not re.search(r"测试状态[：:]\s*ready\b", package, re.I):
        report(findings, level, "content.tutorial_test_not_ready", path, "教程类进入 assets_ready 前必须记录：测试状态：ready")

    completed_screenshots = checked_box_count(screenshot_section)
    result_section = extract_section(package, "实测结果记录", 4)
    result_value = labeled_list_value(result_section, "实际结果")
    conclusion_value = labeled_list_value(result_section, "正文可引用结论")
    evidence_paths = [
        labeled_list_value(result_section, "截图或录屏路径"),
        labeled_list_value(result_section, "输出文件路径"),
    ]
    if completed_screenshots < 3 and not any(value_has_real_content(value) for value in evidence_paths):
        report(
            findings,
            level,
            "content.tutorial_test_evidence_missing",
            path,
            "教程类进入 assets_ready 前至少完成 3 张关键截图，或记录等价录屏/输出文件路径",
        )
    if not value_has_real_content(result_value) or not value_has_real_content(conclusion_value):
        report(
            findings,
            level,
            "content.tutorial_test_result_missing",
            path,
            "教程类进入 assets_ready 前必须填写实际结果和正文可引用结论",
        )


def validate_flagship_research_evidence(
    path: Path,
    text: str,
    findings: list[Finding],
    active: bool,
    stage: str,
    workflow_mode: str,
) -> None:
    if workflow_mode != "flagship":
        return

    stage_order = list(CONTENT_STAGE_STATUS.keys())
    stage_index = stage_order.index(stage) if stage in stage_order else -1
    if stage_index < stage_order.index("market_researched"):
        return

    deep_research = extract_subsection(text, "市场调研", "深度调研")
    research_was_used = stage == "market_researched" or section_has_real_content(
        deep_research
    )
    if not research_was_used:
        return

    level = "error" if active else "warn"
    ledger = extract_section(deep_research, "证据账本", 4)
    sufficiency = extract_section(deep_research, "信息充分性检查", 4)

    usable_rows = 0
    for line in ledger.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 7 or cells[0] in {"编号", ""}:
            continue
        source = cells[3]
        status = cells[6]
        if value_has_real_content(source) and status == "可用":
            usable_rows += 1

    if usable_rows == 0:
        report(
            findings,
            level,
            "content.flagship_evidence_ledger_missing",
            path,
            "旗舰深度调研至少需要 1 条来源完整且使用状态为“可用”的证据账本记录",
        )

    required_labels = [
        "纵向线完整",
        "横向覆盖主要玩家",
        "时效性事实新鲜",
        "交叉洞察有双轴证据",
        "未核实项已隔离",
    ]
    missing_labels = [
        label
        for label in required_labels
        if not value_has_real_content(labeled_list_value(sufficiency, label))
        or "/" in labeled_list_value(sufficiency, label)
    ]
    if missing_labels:
        report(
            findings,
            level,
            "content.flagship_research_sufficiency_incomplete",
            path,
            "旗舰调研信息充分性检查未完成："
            + ", ".join(missing_labels),
        )

    conclusion = labeled_list_value(sufficiency, "结论")
    if not re.fullmatch(r"通过", conclusion.strip()):
        report(
            findings,
            level,
            "content.flagship_research_sufficiency_not_passed",
            path,
            "旗舰调研进入策划前必须记录：信息充分性检查结论：通过",
        )


def validate_content_gate(path: Path, text: str, frontmatter: dict[str, str], findings: list[Finding]) -> None:
    stage = frontmatter.get("stage", "")
    active = top_content_dir(path) in {"_inbox", "待写", "进行中"}
    workflow_mode = content_workflow_mode(frontmatter, text)
    short_post_path = workflow_mode == "quick"
    growth_share_schema_required = (
        active
        or any(frontmatter.get(key, "").strip() for key in CONTENT_GROWTH_BRIEF_KEYS)
        or frontmatter.get("created", "").strip().strip("\"'") >= "2026-07-29"
    )

    if not active and top_content_dir(path) != "已发布":
        return

    gate_rules = [
        ("topics_generated", "选题评估", "判断模块"),
        ("topics_generated", "选题评估", "第二层思考"),
        ("topics_generated", "选题评估", "角度矩阵"),
        ("topics_generated", "选题评估", "7维度评估"),
        ("checked_in", "选题评估", "核心洞见"),
        ("checked_in", "内容Brief", ""),
        ("strategies_generated", "内容策划", "主要矛盾"),
        ("strategies_generated", "内容策划", "第二层思考"),
        ("strategies_generated", "内容策划", "MECE拆解"),
        ("strategies_generated", "内容策划", "内容结构"),
        ("planned", "内容策划", "派活清单"),
        ("assets_ready", "内容策划", "派活清单"),
        ("drafted", "正文", ""),
        ("titled", "标题备选", ""),
        ("titled", "分发素材", "发布包"),
        ("reviewed", "审稿记录", ""),
    ]

    stage_order = list(CONTENT_STAGE_STATUS.keys())
    stage_index = stage_order.index(stage) if stage in stage_order else -1
    for required_stage, parent, child in gate_rules:
        required_index = stage_order.index(required_stage)
        if stage_index < required_index:
            continue
        if workflow_mode != "flagship" and parent == "选题评估" and child == "7维度评估":
            continue
        if workflow_mode != "flagship" and parent == "内容策划" and child in {"第二层思考", "MECE拆解"}:
            continue
        if short_post_path and parent == "内容策划" and stage_index >= stage_order.index("drafted"):
            continue
        content = extract_subsection(text, parent, child) if child else extract_section(text, parent, 2)
        if not section_has_real_content(content):
            label = f"## {parent} > ### {child}" if child else f"## {parent}"
            report(findings, "error" if active else "warn", "content.gate_incomplete", path, f"stage={stage} 需要完成：{label}")

    if stage_index >= stage_order.index("topics_generated") and workflow_mode == "flagship":
        eval_section = extract_subsection(text, "选题评估", "7维度评估")
        score_count = len(re.findall(r"\|\s*\*\*[^|]+\*\*\s*\|\s*(?:[0-9]|10)\s*\|", eval_section))
        if score_count and score_count < 7:
            report(findings, "warn", "content.seven_dimensions_incomplete", path, f"7维度评估只检测到 {score_count} 个评分")

    if stage_index >= stage_order.index("checked_in"):
        missing_brief = [
            key
            for key in ("brief_audience", "brief_user_action", "brief_core_promise")
            if not frontmatter.get(key, "").strip()
        ]
        if missing_brief:
            report(findings, "error" if active else "warn", "content.brief_missing", path, f"内容Brief 缺少关键字段：{', '.join(missing_brief)}")

        if (
            frontmatter.get("content_goal", "").strip().lower() == "growth"
            and growth_share_schema_required
        ):
            missing_share_brief = [
                key
                for key in CONTENT_GROWTH_BRIEF_KEYS
                if not frontmatter.get(key, "").strip()
            ]
            if missing_share_brief:
                report(
                    findings,
                    "error" if active else "warn",
                    "content.growth_share_brief_missing",
                    path,
                    "增长型内容缺少传播入口字段："
                    + ", ".join(missing_share_brief),
                )

    validate_flagship_research_evidence(
        path,
        text,
        findings,
        active,
        stage,
        workflow_mode,
    )

    if stage_index >= stage_order.index("strategies_generated") and not short_post_path:
        conflict_section = extract_subsection(text, "内容策划", "主要矛盾")
        if conflict_section.count("主要矛盾") > 1 and "次要矛盾" not in conflict_section:
            report(findings, "warn", "content.conflict_unclear", path, "主要矛盾区块可能没有区分主次矛盾")

        if workflow_mode == "flagship":
            mece_section = extract_subsection(text, "内容策划", "MECE拆解")
            if "边界检查" not in mece_section:
                report(findings, "error" if active else "warn", "content.mece_boundary_missing", path, "旗舰模式的 MECE拆解缺少边界检查")

        if (
            frontmatter.get("content_goal", "").strip().lower() == "growth"
            and growth_share_schema_required
        ):
            share_section = extract_subsection(text, "内容策划", "传播入口")
            missing_share_labels = [
                label
                for label in (
                    "第一批转发者",
                    "转发给谁",
                    "转发者想表达什么",
                    "可转发载体",
                )
                if not value_has_real_content(labeled_list_value(share_section, label))
            ]
            if missing_share_labels:
                report(
                    findings,
                    "error" if active else "warn",
                    "content.growth_share_entry_incomplete",
                    path,
                    "增长型策划的传播入口未完成："
                    + ", ".join(missing_share_labels),
                )

    if not short_post_path and is_tutorial_content(frontmatter, text):
        validate_tutorial_test_package(path, text, frontmatter, findings, active, stage_index)

    validate_hook_evidence_supplement(
        path,
        text,
        findings,
        active,
        stage,
        workflow_mode,
    )

    if stage_index >= stage_order.index("assets_ready") and not short_post_path:
        dispatch_section = extract_subsection(text, "内容策划", "派活清单")
        evidence_ready = frontmatter.get("evidence_status", "") == "ready" or re.search(r"支撑状态[：:]\s*ready", dispatch_section)
        if not evidence_ready:
            report(findings, "error" if active else "warn", "content.evidence_not_ready", path, "stage=assets_ready 需要 evidence_status=ready 或派活清单支撑状态为 ready")

    if active and stage in {"titled", "reviewed"}:
        title_section = extract_section(text, "标题备选", 2)
        formula_match = re.search(
            r"\*\*最终公式 ID\*\*[：:]\s*([^\r\n]+)",
            title_section,
        )
        evidence_match = re.search(
            r"\*\*最终证据映射\*\*[：:]\s*([^\r\n]+)",
            title_section,
        )
        if not formula_match or not re.search(r"XHS-\d{3}", formula_match.group(1), re.I):
            report(
                findings,
                "error",
                "content.final_title_formula_missing",
                path,
                "titled / reviewed 文件必须记录最终公式 ID（XHS-001—XHS-075）",
            )
        if not evidence_match or not value_has_real_content(evidence_match.group(1)):
            report(
                findings,
                "error",
                "content.final_title_evidence_mapping_missing",
                path,
                "titled / reviewed 文件必须记录最终证据映射",
            )

    if stage_index >= stage_order.index("reviewed"):
        review_section = extract_section(text, "审稿记录", 2)
        required_review_labels = ["事实/数据是否有来源", "平台敏感风险", "版权/引用风险", "标题承诺是否兑现", "CTA 是否合适"]
        missing_review_labels = [label for label in required_review_labels if label not in review_section]
        if missing_review_labels:
            report(findings, "error" if active else "warn", "content.review_risk_checks_missing", path, f"审稿记录缺少发布风险检查项：{', '.join(missing_review_labels)}")
        if (
            frontmatter.get("content_goal", "").strip().lower() == "growth"
            and growth_share_schema_required
            and "传播入口是否成立" not in review_section
        ):
            report(
                findings,
                "error" if active else "warn",
                "content.growth_share_review_missing",
                path,
                "增长型内容的审稿记录缺少：传播入口是否成立",
            )


def validate_content_file(path: Path, findings: list[Finding], stats: dict[str, int], seen_sources: dict[tuple[str, str], Path]) -> None:
    relative = to_posix(path)
    if "/_模板/" in relative or relative.endswith("/README.md"):
        return

    stats["contentFiles"] += 1
    text = read_text(path)
    frontmatter = parse_frontmatter(text)
    top_dir = top_content_dir(path)
    is_active = top_dir in {"_inbox", "待写", "进行中"}
    is_historical = top_dir in {"已发布", "已弃用"}

    if not frontmatter:
        report(findings, "error" if is_active else "warn", "content.frontmatter_missing", path, "活动内容文件缺少 frontmatter" if is_active else "历史内容文件缺少 frontmatter")
        return

    missing_core = [key for key in CONTENT_CORE_KEYS if key not in frontmatter]
    if missing_core:
        report(findings, "error" if is_active else "warn", "content.core_keys_missing", path, f"缺少核心字段：{', '.join(missing_core)}")

    missing_extended = [key for key in CONTENT_EXTENDED_KEYS if key not in frontmatter]
    if missing_extended and is_active:
        report(findings, "warn", "content.extended_keys_missing", path, f"活动文件尚未升级到扩展字段：{', '.join(missing_extended)}")

    stage = frontmatter.get("stage", "")
    status = frontmatter.get("status", "")
    workflow_mode = content_workflow_mode(frontmatter, text)
    short_post_path = workflow_mode == "quick"
    explicit_mode = frontmatter.get("workflow_mode", "")
    if explicit_mode and explicit_mode not in WORKFLOW_MODES:
        report(findings, "error" if is_active else "warn", "content.workflow_mode_invalid", path, f"未知 workflow_mode：{explicit_mode}")
    if stage not in CONTENT_STAGE_STATUS:
        report(findings, "error" if is_active else "warn", "content.stage_invalid", path, f"未知 stage：{stage or '(空)'}")

    allowed_stages = CONTENT_DIR_STAGES.get(top_dir)
    if allowed_stages and stage and stage not in allowed_stages:
        report(findings, "error" if is_active else "warn", "content.stage_dir_mismatch", path, f"stage={stage} 与目录 {top_dir} 不匹配")

    expected_status = CONTENT_STAGE_STATUS.get(stage)
    if expected_status and status and status != expected_status:
        report(findings, "error" if is_active else "warn", "content.stage_status_mismatch", path, f"stage={stage} 期望 status={expected_status}，当前为 {status}")

    agent = frontmatter.get("agent", "")
    if agent and agent not in KNOWN_SKILLS:
        report(findings, "warn", "content.agent_unknown", path, f"agent 未登记：{agent}")

    source_id = frontmatter.get("source_id", "")
    content_angle = frontmatter.get("content_angle", "")
    if source_id and content_angle:
        key = (source_id, content_angle)
        if key in seen_sources:
            report(
                findings,
                "warn",
                "content.duplicate_source_angle",
                path,
                f"全库已存在相同 source_id + content_angle：{to_posix(seen_sources[key])}",
            )
        else:
            seen_sources[key] = path

    if is_active or top_dir == "已发布":
        section_rules = [
            ("原始素材", True),
            ("选题评估", True),
            ("内容Brief", stage in {"checked_in", "market_researched", "strategies_generated", "planned", "assets_ready", "drafted", "titled", "reviewed", "published"}),
            ("市场调研", stage in {"topics_generated", "checked_in", "market_researched", "strategies_generated", "planned", "assets_ready", "drafted", "titled", "reviewed", "published"}),
            ("内容策划", stage in {"strategies_generated", "planned", "assets_ready", "drafted", "titled", "reviewed", "published"} and not (short_post_path and stage in {"drafted", "titled", "reviewed", "published"})),
            ("正文", stage in {"drafted", "titled", "reviewed", "published"}),
            ("标题备选", stage in {"titled", "reviewed", "published"}),
            ("分发素材", stage in {"titled", "reviewed", "published"}),
            ("审稿记录", stage in {"reviewed", "published"}),
            ("发布后数据", top_dir == "已发布" or stage == "published"),
        ]
        for section_name, required in section_rules:
            if required and not has_section(text, section_name):
                code = "content.section_missing_legacy" if top_dir == "已发布" or is_historical else "content.section_missing"
                report(findings, "error" if is_active else "warn", code, path, f"缺少必需区块：## {section_name}")

    if top_dir == "已发布":
        if "published_platforms" not in frontmatter or "published_date" not in frontmatter:
            report(findings, "warn", "content.publish_meta_missing", path, "已发布文件缺少 published_platforms 或 published_date")
        if "**数据填写状态**" not in text:
            report(findings, "warn", "content.data_state_missing", path, "已发布文件缺少数据填写状态标记")

    validate_content_gate(path, text, frontmatter, findings)
    validate_style_chain(path, text, frontmatter, findings, is_active, workflow_mode)
    validate_opening_diversity(path, text, frontmatter, findings, is_active)


def validate_asset_file(path: Path, findings: list[Finding], stats: dict[str, int]) -> None:
    relative = to_posix(path)
    if "/_模板/" in relative or relative.endswith("/README.md"):
        return

    text = read_text(path)
    frontmatter = parse_frontmatter(text)
    managed_by_workflow = "/_inbox/" in relative or "/已整理/" in relative or (frontmatter and ("material_type" in frontmatter or "handler_skill" in frontmatter))
    if not managed_by_workflow:
        return

    stats["assetFiles"] += 1
    if not frontmatter:
        report(findings, "error", "asset.frontmatter_missing", path, "素材资产文件缺少 frontmatter")
        return

    missing_core = [key for key in ASSET_CORE_KEYS if key not in frontmatter]
    if missing_core:
        report(findings, "error", "asset.core_keys_missing", path, f"缺少核心字段：{', '.join(missing_core)}")

    if frontmatter.get("stage") and frontmatter["stage"] not in {"collected", "organized", "archived"}:
        report(findings, "error", "asset.stage_invalid", path, f"未知资产 stage：{frontmatter['stage']}")

    if frontmatter.get("status") and frontmatter["status"] not in {"todo", "in_progress", "done", "archived"}:
        report(findings, "error", "asset.status_invalid", path, f"未知资产 status：{frontmatter['status']}")

    in_inbox = "/_inbox/" in relative
    in_organized = "/已整理/" in relative
    if in_inbox and frontmatter.get("stage") and frontmatter["stage"] != "collected":
        report(findings, "error", "asset.stage_dir_mismatch", path, f"提示词/资产在 _inbox 中时 stage 应为 collected，当前是 {frontmatter['stage']}")

    if in_organized:
        if frontmatter.get("stage") and frontmatter["stage"] != "organized":
            report(findings, "error", "asset.stage_dir_mismatch", path, f"已整理资产的 stage 应为 organized，当前是 {frontmatter['stage']}")
        if frontmatter.get("status") and frontmatter["status"] != "done":
            report(findings, "error", "asset.status_dir_mismatch", path, f"已整理资产的 status 应为 done，当前是 {frontmatter['status']}")

    if not has_section(text, "原始素材"):
        report(findings, "error", "asset.section_missing", path, "缺少必需区块：## 原始素材")

    if frontmatter.get("material_type") == "prompt_asset":
        if not has_section(text, "提示词拆解"):
            report(findings, "error", "asset.prompt_section_missing", path, "提示词资产缺少区块：## 提示词拆解")
        handoff_state = frontmatter.get("content_handoff", "")
        handoff_file = frontmatter.get("content_handoff_file", "")
        if handoff_state == "done":
            if not handoff_file:
                report(findings, "error", "asset.handoff_file_missing", path, "content_handoff=done 但 content_handoff_file 为空")
            else:
                handoff_path = (ROOT / handoff_file).resolve()
                if not handoff_path.exists() or not handoff_path.is_file():
                    report(findings, "error", "asset.handoff_target_missing", path, f"content_handoff_file 不存在：{handoff_file}")
                else:
                    target_frontmatter = parse_frontmatter(read_text(handoff_path)) or {}
                    if target_frontmatter.get("source_id") != frontmatter.get("source_id"):
                        report(findings, "error", "asset.handoff_source_mismatch", path, "handoff 目标与提示词资产的 source_id 不一致")
                    if target_frontmatter.get("content_angle") != "prompt_list":
                        report(findings, "error", "asset.handoff_angle_mismatch", path, "handoff 目标的 content_angle 应为 prompt_list")
    else:
        if not has_section(text, "可复用资产"):
            report(findings, "error", "asset.section_missing", path, "素材资产缺少区块：## 可复用资产")
        if frontmatter.get("material_type") == "content_unit":
            unit_id = frontmatter.get("unit_id", "")
            unit_type = frontmatter.get("unit_type", "")
            if not re.fullmatch(r"CU-\d{8}-\d{3,}", unit_id):
                report(findings, "error", "asset.unit_id_invalid", path, f"内容单元 unit_id 无效：{unit_id or '缺失'}")
            if unit_type not in CONTENT_UNIT_TYPES:
                report(findings, "error", "asset.unit_type_invalid", path, f"内容单元 unit_type 无效：{unit_type or '缺失'}")
            if not has_section(text, "关系"):
                report(findings, "error", "asset.unit_relations_missing", path, "内容单元缺少区块：## 关系")


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda item: (0 if item.level == "error" else 1, item.path, item.code))


def print_text_report(findings: list[Finding], stats: dict[str, int]) -> None:
    errors = [item for item in findings if item.level == "error"]
    warnings = [item for item in findings if item.level == "warn"]

    print("工作流校验报告")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"- 内容文件: {stats['contentFiles']}")
    print(f"- 资产文件: {stats['assetFiles']}")
    print(f"- 错误: {len(errors)}")
    print(f"- 警告: {len(warnings)}")

    if not findings:
        print("✅ 当前没有发现校验问题")
        return

    for item in findings:
        prefix = "ERROR" if item.level == "error" else "WARN"
        print(f"{prefix} {item.path or '(无路径)'} | {item.code} | {item.message}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    findings: list[Finding] = []
    stats = {"contentFiles": 0, "assetFiles": 0}
    seen_sources: dict[tuple[str, str], Path] = {}

    for path in walk_markdown_files(CONTENT_ROOT):
        validate_content_file(path, findings, stats, seen_sources)

    for path in walk_markdown_files(MATERIAL_ROOT):
        validate_asset_file(path, findings, stats)

    findings = sort_findings(findings)
    errors = len([item for item in findings if item.level == "error"])

    if has_flag("--json"):
        print(
            json.dumps(
                {
                    "stats": stats,
                    "errors": errors,
                    "warnings": len([item for item in findings if item.level == "warn"]),
                    "findings": [item.__dict__ for item in findings],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_text_report(findings, stats)

    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
