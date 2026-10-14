#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PUBLISHED_ROOT = ROOT / "选题库" / "已发布"
REVIEW_FILE = ROOT / "数据统计" / "2026-03-W2-复盘.md"


REVIEW_TABLE = """**7维度回顾**：哪个维度预判准了？哪个偏了？

| 维度 | 预判评分 | 实际表现 | 准确度 | 备注 |
|------|---------|---------|--------|------|
| 打断力 | | | | |
| 认知刷新 | | | | |
| 人性触发 | | | | |
| 身份锚定 | | | | |
| 作品支撑 | | | | |
| 可收藏性 | | | | |
| 工作量 | | | | |
"""


PUBLISHED_COLLECTIBILITY = {
    "DeepSeek_V4": ("⭐", "技术解读为主，可复用清单较少，收藏动力偏弱"),
    "别学Skills": ("✓✓", "有对比表和判断标准，但缺少可直接复制模板"),
    "版权漏洞与内容工厂": ("⭐", "评论分析为主，读完即走，反复查看价值较弱"),
    "Seedance2.0到底怎么玩": ("⭐⭐⭐", "技巧清单 + 提示词示例 + 实操步骤，适合反复查看"),
}


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return path.read_text(encoding=encoding).replace("\r\n", "\n")
        except Exception:
            continue
    return path.read_text(errors="ignore").replace("\r\n", "\n")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def to_posix(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def has_flag(name: str) -> bool:
    return name in sys.argv


def collectibility_for(path: Path, ratings: list[str]) -> tuple[str, str]:
    relative = to_posix(path)
    for key, value in PUBLISHED_COLLECTIBILITY.items():
        if key in relative:
            return value
    uses_checkmarks = any("✓" in rating for rating in ratings)
    return ("✓", "历史文章迁移补齐：可收藏性待后续人工细化") if uses_checkmarks else ("⭐", "历史文章迁移补齐：可收藏性待后续人工细化")


def normalize_dimension(label: str) -> str:
    mapping = {
        "认知颠覆": "认知刷新",
        "情绪共振": "人性触发",
        "你独有": "作品支撑",
        "可写性": "工作量",
    }
    cleaned = label.strip().strip("*")
    return mapping.get(cleaned, cleaned)


def migrate_eval_table(text: str, path: Path) -> tuple[str, bool]:
    pattern = re.compile(
        r"(?ms)(^#{2,3}\s+)6维度评估([^\n]*)\n\n(\| 维度 \|[^\n]*\n\|[-| ]+\|\n(?:\|[^\n]+\n)+)"
    )

    changed = False

    def replace(match: re.Match) -> str:
        nonlocal changed
        heading_prefix, heading_suffix, table_text = match.group(1), match.group(2), match.group(3)
        lines = [line for line in table_text.strip("\n").split("\n") if line.strip()]
        header = lines[:2]
        rows = []
        ratings = []

        for line in lines[2:]:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 3:
                continue
            label = normalize_dimension(cells[0])
            rating = cells[1]
            reason = cells[2]
            ratings.append(rating)
            rows.append((label, rating, reason))

        row_map = {label: (rating, reason) for label, rating, reason in rows}
        if "可收藏性" not in row_map:
            row_map["可收藏性"] = collectibility_for(path, ratings)

        ordered_labels = ["打断力", "认知刷新", "人性触发", "身份锚定", "作品支撑", "可收藏性", "工作量"]
        rebuilt_rows = []
        for label in ordered_labels:
            rating, reason = row_map.get(label, ("", ""))
            rebuilt_rows.append(f"| **{label}** | {rating} | {reason} |")

        changed = True
        return f"{heading_prefix}7维度评估{heading_suffix}\n\n" + "\n".join(header + rebuilt_rows) + "\n"

    updated = pattern.sub(replace, text)
    updated = updated.replace("`## 6维度评估`", "`## 7维度评估`")
    return updated, changed or updated != text


def migrate_review_placeholder(text: str) -> tuple[str, bool]:
    pattern = re.compile(
        r"(?ms)(## 复盘\s*\n(?:<!--.*?-->\s*\n)?\s*)\*\*(?:6|7)维度回顾\*\*：哪个维度预判准了？哪个偏了？\s*\n\s*(\*\*下次可以试\*\*：)"
    )

    changed = False

    def replace(match: re.Match) -> str:
        nonlocal changed
        changed = True
        return f"{match.group(1)}{REVIEW_TABLE}\n{match.group(2)}"

    updated = pattern.sub(replace, text)
    return updated, changed


def migrate_review_report(text: str) -> tuple[str, bool]:
    updated = text

    replacements = [
        ("**6维度回顾**", "**7维度回顾**"),
        ("## 🔄 6维度预判准确度", "## 🔄 7维度预判准确度"),
        ("对比发布前的6维度评估和实际数据表现，校准评估体系。", "对比发布前的7维度评估和实际数据表现，校准评估体系。"),
        ("#### 1. 6维度评估体系升级", "#### 1. 7维度评估体系升级"),
        ("**新增第7维度：可收藏性**", "**补齐第7维度：可收藏性**"),
        ('新增"可收藏性"维度到 6 维度评估体系', '新增"可收藏性"维度到 7 维度评估体系'),
    ]

    for old, new in replacements:
        updated = updated.replace(old, new)

    if "| **可收藏性** |" not in updated:
        updated = updated.replace(
            "| **作品支撑** | ✅ 准确 | 有真实作品支撑的文章表现更好 |\n| **工作量** | ❌ 无关 | 工作量与数据表现无明显相关性 |",
            "| **作品支撑** | ✅ 准确 | 有真实作品支撑的文章表现更好 |\n| **可收藏性** | ✅ 准确 | Seedance 22.7% 收藏率证明“可收藏性”是爆款关键指标 |\n| **工作量** | ❌ 无关 | 工作量与数据表现无明显相关性 |",
        )

    block_replacements = [
        (
            "**7维度回顾**：\n- **打断力**：⭐⭐⭐ 预判准确（紧迫 + 相关）\n- **认知刷新**：⭐⭐⭐ 预判准确（多模态 ≠ 文生视频）\n- **人性触发**：⭐⭐ 预判偏低（实际触发了\"好奇 + 懒 + 掌控\"）\n- **身份锚定**：⭐⭐⭐ 预判准确（内容创作者、设计师）\n- **作品支撑**：⭐⭐ 预判准确（有实测案例）",
            "**7维度回顾**：\n- **打断力**：⭐⭐⭐ 预判准确（紧迫 + 相关）\n- **认知刷新**：⭐⭐⭐ 预判准确（多模态 ≠ 文生视频）\n- **人性触发**：⭐⭐ 预判偏低（实际触发了\"好奇 + 懒 + 掌控\"）\n- **身份锚定**：⭐⭐⭐ 预判准确（内容创作者、设计师）\n- **作品支撑**：⭐⭐ 预判准确（有实测案例）\n- **可收藏性**：⭐⭐⭐ 预判准确（提示词技巧 + 操作步骤带来极强收藏动力）",
        ),
        (
            "**7维度回顾**：\n- **打断力**：⭐⭐⭐ 预判偏高（紧迫感不足，V4 未发布）\n- **认知刷新**：⭐⭐⭐ 预判准确（查字典 vs 推理）\n- **身份锚定**：⭐⭐ 预判准确但受众窄",
            "**7维度回顾**：\n- **打断力**：⭐⭐⭐ 预判偏高（紧迫感不足，V4 未发布）\n- **认知刷新**：⭐⭐⭐ 预判准确（查字典 vs 推理）\n- **身份锚定**：⭐⭐ 预判准确但受众窄\n- **可收藏性**：⭐ 预判准确（技术解读价值有，但缺少可直接带走的模板）",
        ),
        (
            "**7维度回顾**：\n- **打断力**：⭐⭐⭐ 预判准确（意外 + 相关）\n- **认知刷新**：⭐⭐⭐ 预判准确\n- **身份锚定**：⭐⭐ 预判准确但受众窄（被新概念搞焦虑的人）",
            "**7维度回顾**：\n- **打断力**：⭐⭐⭐ 预判准确（意外 + 相关）\n- **认知刷新**：⭐⭐⭐ 预判准确\n- **身份锚定**：⭐⭐ 预判准确但受众窄（被新概念搞焦虑的人）\n- **可收藏性**：⭐⭐ 预判准确（对比表和判断标准有一定收藏价值）",
        ),
        (
            "**7维度回顾**：\n- **打断力**：⭐⭐⭐ 预判偏高（意外感不足，读者不关心）\n- **认知刷新**：⭐⭐⭐ 预判偏高（内容工厂闭环对读者价值不大）\n- **人性触发**：⭐⭐⭐ 预判偏高（恐惧感未触发）\n- **身份锚定**：⭐⭐ 预判准确但受众太窄",
            "**7维度回顾**：\n- **打断力**：⭐⭐⭐ 预判偏高（意外感不足，读者不关心）\n- **认知刷新**：⭐⭐⭐ 预判偏高（内容工厂闭环对读者价值不大）\n- **人性触发**：⭐⭐⭐ 预判偏高（恐惧感未触发）\n- **身份锚定**：⭐⭐ 预判准确但受众太窄\n- **可收藏性**：⭐ 预判偏高（宏观评论难形成反复查看价值）",
        ),
    ]

    for old, new in block_replacements:
        updated = updated.replace(old, new)

    return updated, updated != text


def migrate_published_files(apply: bool) -> list[str]:
    changed_paths = []
    for path in sorted(PUBLISHED_ROOT.rglob("*.md")):
        if not path.is_file():
            continue
        original = read_text(path)
        updated, changed_eval = migrate_eval_table(original, path)
        updated, changed_review = migrate_review_placeholder(updated)
        if changed_eval or changed_review:
            changed_paths.append(to_posix(path))
            if apply:
                write_text(path, updated)
    return changed_paths


def migrate_review_file(apply: bool) -> bool:
    if not REVIEW_FILE.exists():
        return False
    original = read_text(REVIEW_FILE)
    updated, changed = migrate_review_report(original)
    if changed and apply:
        write_text(REVIEW_FILE, updated)
    return changed


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    apply = has_flag("--apply")
    changed_files = migrate_published_files(apply)
    changed_review = migrate_review_file(apply)

    print(f"6→7 维度迁移 | 模式: {'apply' if apply else 'check'}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"- 已发布文章待处理: {len(changed_files)}")
    if changed_files:
        for item in changed_files:
            print(f"  · {item}")
    print(f"- 周复盘待处理: {'是' if changed_review else '否'}")

    if apply:
        print("✅ 迁移完成")


if __name__ == "__main__":
    main()
