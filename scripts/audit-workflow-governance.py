#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from workflow_config import KNOWN_SKILLS, ROUTE_RULES, ROOT


WARNING_BUDGET = 28 * 1024
HARD_BUDGET = 32 * 1024


@dataclass
class Finding:
    level: str
    code: str
    path: str
    message: str


def relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def add(
    findings: list[Finding],
    level: str,
    code: str,
    path: Path,
    message: str,
) -> None:
    findings.append(Finding(level, code, relative(path), message))


def markdown_files() -> list[Path]:
    files = [ROOT / "AGENTS.md", ROOT / "CLAUDE.md"]
    files.extend(sorted((ROOT / "skills").rglob("*.md")))
    files.extend(sorted((ROOT / "选题库" / "_模板").glob("*.md")))
    return [path for path in files if path.is_file()]


def local_link_targets(path: Path, text: str) -> list[tuple[str, Path]]:
    targets: list[tuple[str, Path]] = []
    for raw in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = raw.strip().strip("<>")
        if (
            not target
            or target.startswith(("#", "http://", "https://", "mailto:", "app://"))
            or target in {"链接", "URL", "url"}
            or any(token in target for token in ("${", "{{", "<skill", "<path", "xxx"))
        ):
            continue
        clean = target.split("#", 1)[0].strip()
        if not clean:
            continue
        resolved = (path.parent / clean).resolve()
        targets.append((target, resolved))
    return targets


def audit_rule_budget(findings: list[Finding]) -> dict[str, object]:
    path = ROOT / "AGENTS.md"
    size = path.stat().st_size
    if size > HARD_BUDGET:
        add(
            findings,
            "error",
            "governance.agents_over_hard_budget",
            path,
            f"AGENTS.md 为 {size} 字节，超过 32 KiB 默认加载上限",
        )
    elif size > WARNING_BUDGET:
        add(
            findings,
            "warn",
            "governance.agents_near_budget",
            path,
            f"AGENTS.md 为 {size} 字节，已超过 28 KiB 警戒线",
        )
    return {
        "status": "verified-current" if size <= WARNING_BUDGET else "pending",
        "bytes": size,
        "warningBudget": WARNING_BUDGET,
        "hardBudget": HARD_BUDGET,
    }


def audit_links(findings: list[Finding]) -> dict[str, object]:
    checked = 0
    missing = 0
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for raw, target in local_link_targets(path, text):
            checked += 1
            if target.exists():
                continue
            missing += 1
            add(
                findings,
                "error",
                "governance.dead_local_link",
                path,
                f"本地引用不存在：{raw}",
            )
    return {
        "status": "verified-current" if missing == 0 else "pending",
        "checked": checked,
        "missing": missing,
    }


def audit_skills(findings: list[Finding]) -> dict[str, object]:
    missing_registered = 0
    for name, raw_path in KNOWN_SKILLS.items():
        path = ROOT / raw_path
        if path.is_file():
            continue
        missing_registered += 1
        add(
            findings,
            "error",
            "governance.registered_skill_missing",
            ROOT / "scripts" / "workflow_config.py",
            f"KNOWN_SKILLS 注册的 {name} 不存在：{raw_path}",
        )

    skill_files = sorted((ROOT / "skills").rglob("SKILL.md"))
    frontmatter_errors = 0
    long_skills = 0
    for path in skill_files:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not match or not re.search(r"^name:\s*.+$", match.group(1), re.M) or not re.search(
            r"^description:\s*(?:.+|[>|]-?)$", match.group(1), re.M
        ):
            frontmatter_errors += 1
            add(
                findings,
                "error",
                "governance.skill_frontmatter_invalid",
                path,
                "SKILL.md 缺少可识别的 name 或 description",
            )
        if len(lines) >= 500:
            long_skills += 1
            add(
                findings,
                "warn",
                "governance.skill_line_budget",
                path,
                f"SKILL.md 为 {len(lines)} 行，建议拆分到一层 references",
            )

    return {
        "status": (
            "verified-current"
            if missing_registered == 0 and frontmatter_errors == 0
            else "pending"
        ),
        "registered": len(KNOWN_SKILLS),
        "discovered": len(skill_files),
        "longSkills": long_skills,
    }


def audit_routes(findings: list[Finding]) -> dict[str, object]:
    seen: dict[str, str] = {}
    duplicates = 0
    for route in ROUTE_RULES:
        for trigger in route["triggers"]:
            previous = seen.get(trigger)
            if previous and previous != route["intent"]:
                duplicates += 1
                add(
                    findings,
                    "error",
                    "governance.duplicate_trigger",
                    ROOT / "scripts" / "workflow_config.py",
                    f"触发词“{trigger}”同时属于“{previous}”和“{route['intent']}”",
                )
            seen[trigger] = route["intent"]
    return {
        "status": "verified-current" if duplicates == 0 else "pending",
        "routes": len(ROUTE_RULES),
        "triggers": len(seen),
        "duplicates": duplicates,
    }


def audit_required_surfaces(findings: list[Finding]) -> dict[str, object]:
    required = [
        ROOT / "skills" / "_通用" / "工作流详细规范.md",
        ROOT / "scripts" / "workflow_config.py",
        ROOT / "scripts" / "validate-workflow.py",
        ROOT / "tests",
        ROOT / "evals" / "trigger-eval.json",
        ROOT / "evals" / "workflow-scenarios.json",
        ROOT / "选题库" / "_模板" / "选题模板-标准.md",
        ROOT / "选题库" / "_模板" / "选题模板.md",
        ROOT / "素材库" / "_模板" / "内容单元模板.md",
        ROOT / "skills" / "_通用" / "内容单元与关系模型.md",
        ROOT / "skills" / "_通用" / "分级扩张批处理合同.md",
        ROOT / "scripts" / "audit-content-units.py",
        ROOT / "scripts" / "plan-batch-expansion.py",
    ]
    missing = 0
    for path in required:
        if path.exists():
            continue
        missing += 1
        add(
            findings,
            "error",
            "governance.required_surface_missing",
            path,
            "工作流治理必需面不存在",
        )
    return {
        "status": "verified-current" if missing == 0 else "pending",
        "checked": len(required),
        "missing": missing,
    }


def audit_memory_contract(findings: list[Finding]) -> dict[str, object]:
    path = ROOT / "skills" / "_通用" / "会话记忆.md"
    required_headings = [
        "当前进行中的任务",
        "用户已否决的方向",
        "待验证假设",
        "最近 3 次对话关键决策",
        "临时偏好记录",
        "未完成的讨论话题",
    ]
    if not path.is_file():
        add(findings, "error", "governance.memory_missing", path, "会话记忆文件不存在")
        return {"status": "pending", "checked": len(required_headings), "missing": len(required_headings)}

    text = path.read_text(encoding="utf-8")
    missing = [
        heading
        for heading in required_headings
        if not re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.M)
    ]
    for heading in missing:
        add(
            findings,
            "error",
            "governance.memory_section_missing",
            path,
            f"会话记忆缺少区块：## {heading}",
        )
    return {
        "status": "verified-current" if not missing else "pending",
        "checked": len(required_headings),
        "missing": len(missing),
    }


def build_report() -> dict[str, object]:
    findings: list[Finding] = []
    surfaces = {
        "ruleBudget": audit_rule_budget(findings),
        "localLinks": audit_links(findings),
        "skills": audit_skills(findings),
        "routes": audit_routes(findings),
        "requiredSurfaces": audit_required_surfaces(findings),
        "memoryContract": audit_memory_contract(findings),
        "runtime": {
            "status": "out-of-scope",
            "note": "本脚本只读审计静态治理面；运行态由 validate-workflow 与 pytest 单独验证",
        },
        "memory": {
            "status": "verified-current",
            "note": "结构由 memoryContract 审计；具体内容仍需按事实人工维护",
        },
    }
    errors = sum(item.level == "error" for item in findings)
    warnings = sum(item.level == "warn" for item in findings)
    return {
        "surfaces": surfaces,
        "findings": [asdict(item) for item in findings],
        "summary": {"errors": errors, "warnings": warnings},
    }


def print_text(report: dict[str, object]) -> None:
    print("工作流治理审计")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for name, surface in report["surfaces"].items():
        details = ", ".join(
            f"{key}={value}"
            for key, value in surface.items()
            if key not in {"status", "note"}
        )
        suffix = f" | {details}" if details else ""
        print(f"- {name}: {surface['status']}{suffix}")
        if surface.get("note"):
            print(f"  · {surface['note']}")
    print(
        f"- 结果: 错误 {report['summary']['errors']} | "
        f"警告 {report['summary']['warnings']}"
    )
    for finding in report["findings"]:
        print(
            f"{finding['level'].upper()} {finding['path']} | "
            f"{finding['code']} | {finding['message']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="只读审计内容工作流治理面")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
