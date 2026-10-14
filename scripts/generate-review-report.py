#!/usr/bin/env python3

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from workflow_lib import atomic_write_text, parse_frontmatter_document, read_text, scalar_text


ROOT = Path(__file__).resolve().parent.parent
PUBLISHED_ROOT = ROOT / "选题库" / "已发布"
TEMPLATE_PATH = ROOT / "数据统计" / "复盘记录-模板.md"

DIMENSIONS = ["打断力", "认知刷新", "人性触发", "身份锚定", "作品支撑", "可收藏性", "工作量"]


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


def write_text(path: Path, content: str) -> None:
    atomic_write_text(path, content)


def strip_quotes(value: str) -> str:
    value = str(value or "").strip()
    if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict:
    document = parse_frontmatter_document(text)
    if not document:
        return {}
    return {key: scalar_text(value) if not isinstance(value, list) else value for key, value in document.data.items()}


def parse_date(value: str):
    value = strip_quotes(value)
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", value)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%d").date()


def extract_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^## {re.escape(heading)}\s*$", re.M)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    rest = text[start:]
    next_match = re.search(r"\n## [^\n]+", rest)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end]


def extract_subsection(text: str, heading: str) -> str:
    pattern = re.compile(rf"^### {re.escape(heading)}\s*$", re.M)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    rest = text[start:]
    next_match = re.search(r"\n### [^\n]+|\n## [^\n]+", rest)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def markdown_table_rows(section: str) -> list[list[str]]:
    rows = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        if re.match(r"^\|[-| :]+\|?$", line.replace("\t", "")):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


def score_from_rating(raw: str) -> float | None:
    raw = raw.strip()
    if not raw:
        return None
    if raw.isdigit():
        return float(raw)
    if "⭐" in raw:
        return float(raw.count("⭐")) / 3 * 10
    if "✓" in raw:
        return float(raw.count("✓")) / 3 * 10
    return None


def article_type(title: str) -> str:
    if any(keyword in title for keyword in ["怎么玩", "从入门到", "跑通", "技巧"]):
        return "工具教程/实操"
    if any(keyword in title for keyword in ["OpenAI", "DeepSeek", "模型"]):
        return "技术解读"
    if any(keyword in title for keyword in ["漏洞", "工厂", "大棋"]):
        return "热点评论"
    return "观点/方法论"


def week_of_month(target: date) -> int:
    return math.ceil(target.day / 7)


@dataclass
class Article:
    path: Path
    title: str
    priority: str
    created: date | None
    published_date: date | None
    platforms: list[str]
    primary_platform: str
    metric_window: str
    reads: int
    interactions: int
    collects: int
    comments: int
    interaction_rate: float
    collect_rate: float
    type_name: str
    dimensions: dict[str, tuple[str, str]]
    core_insight: str
    formula_ids: list[str]
    content_goal: str


def parse_publish_metrics(text: str) -> tuple[str, dict[str, int], str]:
    publish_section = extract_section(text, "发布后数据")
    simple_rows = markdown_table_rows(publish_section)
    if simple_rows and simple_rows[0][:5] == ["平台", "记录日期", "阅读量", "点赞", "收藏"]:
        best_platform = ""
        best_metrics = {"阅读量": 0, "点赞": 0, "在看": 0, "收藏": 0, "评论": 0, "转发": 0}
        best_window = ""
        for row in simple_rows[1:]:
            if len(row) < 5:
                continue
            reads_raw = row[2].replace(",", "").strip()
            if not reads_raw.isdigit():
                continue
            reads = int(reads_raw)
            if reads <= best_metrics["阅读量"]:
                continue
            best_platform = row[0] or "未标注平台"
            best_window = row[1] or "最新快照"
            best_metrics["阅读量"] = reads
            best_metrics["点赞"] = int(row[3].replace(",", "")) if row[3].replace(",", "").strip().isdigit() else 0
            best_metrics["收藏"] = int(row[4].replace(",", "")) if row[4].replace(",", "").strip().isdigit() else 0
        return best_platform or "未标注平台", best_metrics, best_window

    platform_blocks = {
        "微信公众号": extract_subsection(publish_section, "微信公众号"),
        "小红书": extract_subsection(publish_section, "小红书"),
        "知乎": extract_subsection(publish_section, "知乎"),
    }

    best_platform = "微信公众号"
    best_metrics = {"阅读量": 0, "点赞": 0, "在看": 0, "收藏": 0, "评论": 0, "转发": 0}
    best_window = ""

    for platform_name, block in platform_blocks.items():
        if not block:
            continue
        rows = markdown_table_rows(block)
        if len(rows) < 2:
            continue
        headers = rows[0]
        candidate_columns = list(range(min(len(headers), 4) - 1, 0, -1))
        chosen_column = None
        for column in candidate_columns:
            read_row = next((row for row in rows[1:] if row and row[0] == "阅读量"), None)
            if read_row and len(read_row) > column and read_row[column].replace(",", "").strip().isdigit():
                chosen_column = column
                break
        if chosen_column is None:
            continue

        metrics = {"阅读量": 0, "点赞": 0, "在看": 0, "收藏": 0, "评论": 0, "转发": 0}
        for row in rows[1:]:
            if len(row) <= chosen_column:
                continue
            metric = row[0]
            value = row[chosen_column].replace(",", "").strip()
            if metric in metrics and value.isdigit():
                metrics[metric] = int(value)
        if metrics["阅读量"] > best_metrics["阅读量"]:
            best_platform = platform_name
            best_metrics = metrics
            best_window = headers[chosen_column]

    return best_platform, best_metrics, best_window


def parse_dimensions(text: str) -> dict[str, tuple[str, str]]:
    eval_match = re.search(r"(?ms)^#{2,3}\s+7维度评估[^\n]*\n\n(\| 维度 \|[^\n]*\n\|[-| ]+\|\n(?:\|[^\n]+\n)+)", text)
    dimensions = {}
    if not eval_match:
        return dimensions
    rows = markdown_table_rows(eval_match.group(1))
    for row in rows[1:]:
        if len(row) < 3:
            continue
        label = row[0].strip("* ")
        dimensions[label] = (row[1].strip(), row[2].strip())
    return dimensions


def parse_formula_ids(text: str) -> list[str]:
    title_section = extract_section(text, "标题备选")
    match = re.search(r"\*\*最终公式 ID\*\*[：:]\s*([^\r\n]+)", title_section)
    if not match:
        return []
    return sorted(set(re.findall(r"XHS-\d{3}", match.group(1).upper())))


def formula_category(formula_id: str) -> str:
    match = re.fullmatch(r"XHS-(\d{3})", formula_id)
    if not match:
        return "未识别"
    number = int(match.group(1))
    ranges = [
        (1, 7, "A 结果与成本"),
        (8, 13, "B 时间与效率"),
        (14, 20, "C 反差与意外"),
        (21, 26, "D 问题与症状"),
        (27, 32, "E 身份与场景"),
        (33, 39, "F 教程与步骤"),
        (40, 45, "G 清单与模板"),
        (46, 51, "H 工具比较与选择"),
        (52, 57, "I 案例与复盘"),
        (58, 63, "J 热点与变化"),
        (64, 69, "K 观点与方法论"),
        (70, 75, "L 互动与讨论"),
    ]
    return next(
        (label for start, end, label in ranges if start <= number <= end),
        "未识别",
    )


def parse_article(path: Path) -> Article | None:
    text = read_text(path)
    frontmatter = parse_frontmatter(text)
    if strip_quotes(frontmatter.get("stage", "")) != "published":
        return None

    title = strip_quotes(frontmatter.get("title", "")) or path.stem
    platforms_raw = frontmatter.get("published_platforms", "")
    if isinstance(platforms_raw, list):
        platforms = [str(item).strip() for item in platforms_raw if str(item).strip()]
    else:
        platforms = [item.strip() for item in strip_quotes(platforms_raw).strip("[]").split(",") if item.strip()]
    primary_platform, metrics, metric_window = parse_publish_metrics(text)
    reads = metrics.get("阅读量", 0)
    likes = metrics.get("点赞", 0)
    watches = metrics.get("在看", 0)
    collects = metrics.get("收藏", 0)
    comments = metrics.get("评论", 0)
    shares = metrics.get("转发", 0)
    interactions = likes + watches + collects + comments + shares
    interaction_rate = round(interactions / reads * 100, 1) if reads else 0.0
    collect_rate = round(collects / reads * 100, 1) if reads else 0.0

    core_insight_section = extract_subsection(text, "核心洞见")
    insight_match = re.search(r"> (.+)", core_insight_section)
    core_insight = insight_match.group(1).strip() if insight_match else ""

    return Article(
        path=path,
        title=title,
        priority=strip_quotes(frontmatter.get("priority", "")),
        created=parse_date(frontmatter.get("created", "")),
        published_date=parse_date(frontmatter.get("published_date", "")),
        platforms=platforms,
        primary_platform=primary_platform,
        metric_window=metric_window,
        reads=reads,
        interactions=interactions,
        collects=collects,
        comments=comments,
        interaction_rate=interaction_rate,
        collect_rate=collect_rate,
        type_name=article_type(title),
        dimensions=parse_dimensions(text),
        core_insight=core_insight,
        formula_ids=parse_formula_ids(text),
        content_goal=strip_quotes(frontmatter.get("content_goal", "")) or "未标注",
    )


def grade_for_article(article: Article, max_reads: int) -> str:
    if max_reads <= 0:
        return "C"
    ratio = article.reads / max_reads
    if ratio >= 0.8:
        return "S"
    if ratio >= 0.2:
        return "A"
    if ratio >= 0.05:
        return "B"
    return "C"


def dimension_accuracy(article: Article, dimension: str) -> str:
    rating, _ = article.dimensions.get(dimension, ("", ""))
    score = score_from_rating(rating)
    if score is None:
        return "待补"

    if dimension == "可收藏性":
        if article.collect_rate >= 10 and score >= 8:
            return "准确"
        if article.collect_rate < 3 and score >= 8:
            return "偏高"
        if article.collect_rate >= 5 and score < 6:
            return "偏低"
        return "准确"

    if dimension == "工作量":
        return "弱相关"

    if article.reads >= 5000 and score >= 8:
        return "准确"
    if article.reads < 1000 and score >= 8:
        return "偏高"
    if article.reads >= 5000 and score < 6:
        return "偏低"
    return "准确"


def aggregate_dimension_accuracy(articles: list[Article]) -> list[tuple[str, str, str]]:
    rows = []
    for dimension in DIMENSIONS:
        statuses = [dimension_accuracy(article, dimension) for article in articles if dimension in article.dimensions]
        if not statuses:
            rows.append((dimension, "待补", "暂无评估数据"))
            continue

        if dimension == "工作量":
            rows.append((dimension, "弱相关", "工作量与数据表现相关性弱，建议继续保留但降低判断权重"))
            continue

        counts = {status: statuses.count(status) for status in {"准确", "偏高", "偏低", "待补"}}
        dominant = max(counts.items(), key=lambda item: item[1])[0]

        if dimension == "可收藏性":
            insight = "高收藏文章明显更强，建议继续强化模板、清单、提示词等可带走内容"
        elif dominant == "偏高":
            insight = "当前预判普遍偏高，后续需要更严格的需求验证"
        elif dominant == "偏低":
            insight = "当前预判普遍偏低，说明这一维度价值被低估"
        else:
            insight = "当前预判整体稳定，可继续沿用"

        rows.append((dimension, dominant, insight))
    return rows


def build_overview_table(articles: list[Article], max_reads: int) -> str:
    lines = [
        "| # | 标题 | 平台 | 播放/阅读 | 互动(转评赞) | 完播率/读完率 | 涨粉 | 综合评级 |",
        "|---|------|------|----------|-------------|--------------|------|---------|",
    ]
    for index, article in enumerate(articles, start=1):
        lines.append(
            f"| {index} | {article.title} | {article.primary_platform} | {article.reads:,} | {article.interactions} | - | - | {grade_for_article(article, max_reads)} |"
        )
    return "\n".join(lines)


def build_top_section(article: Article, rank: int, max_reads: int) -> str:
    reasons = []
    if article.type_name == "工具教程/实操":
        reasons.append("选题：工具教程 / 实操型内容命中强需求，窗口期价值高")
    elif article.type_name == "技术解读":
        reasons.append("选题：技术解读类内容有明确受众，但对泛流量不友好")
    else:
        reasons.append(f"选题：{article.type_name}，具备一定辨识度")

    if article.collect_rate >= 10:
        reasons.append("结构：可收藏性极强，读者愿意反复查看")
    elif article.collect_rate >= 3:
        reasons.append("结构：有一定收藏价值，说明内容具备带走属性")
    else:
        reasons.append("结构：收藏驱动力一般，更多依赖即时阅读")

    if article.core_insight:
        reasons.append(f"金句/开头：核心洞见“{article.core_insight}”有明确记忆点")

    dimension_rows = []
    for dimension in DIMENSIONS:
        if dimension not in article.dimensions:
            continue
        dimension_rows.append(f"  - **{dimension}**：{dimension_accuracy(article, dimension)}")

    return "\n".join(
        [
            f"### {rank}. {article.title}",
            f"- **数据亮点**：阅读量 {article.reads:,} / 互动率 {article.interaction_rate}% / 收藏率 {article.collect_rate}%",
            "- **成功原因**：",
            *[f"  - {reason}" for reason in reasons],
            "- **7维度回顾**：",
            *dimension_rows,
            "- **可复用点**：",
            "  - [ ] 金句已存入 `素材库/金句/`",
            "  - [ ] 结构已存入 `素材库/爆款结构/`",
            "  - [ ] 概念已存入 `素材库/核心概念/`",
        ]
    )


def build_bottom_section(article: Article, rank: int) -> str:
    reasons = []
    if article.type_name == "热点评论":
        reasons.append("选题：宏观评论类内容缺少“与我有关”，更依赖个人品牌或独家信息")
    elif article.type_name == "观点/方法论":
        reasons.append("选题：观点型内容需要更强的实操案例支撑")
    else:
        reasons.append("选题：需求面偏窄，触达范围有限")

    if article.collect_rate >= 3:
        reasons.append("结构：有一定收藏价值，但传播面不足")
    else:
        reasons.append("结构：缺少让读者保存反复查看的理由")

    if article.interaction_rate < 5:
        reasons.append("违规/敏感点：未见明显异常，更像是需求验证不足")
    else:
        reasons.append("违规/敏感点：互动不算差，问题更偏向分发和选题")

    return "\n".join(
        [
            f"### {rank}. {article.title}",
            f"- **数据表现**：阅读量 {article.reads:,} / 互动率 {article.interaction_rate}% / 收藏率 {article.collect_rate}%",
            "- **失败原因**：",
            *[f"  - {reason}" for reason in reasons],
            "- **7维度回顾**：",
            *[
                f"  - **{dimension}**：{dimension_accuracy(article, dimension)}"
                for dimension in DIMENSIONS
                if dimension in article.dimensions and dimension != "工作量"
            ],
            "- **改进措施**：下次遇到类似选题，优先补强需求验证、可收藏性和实操案例",
        ]
    )


def build_formula_feedback(articles: list[Article]) -> str:
    tracked = [article for article in articles if article.formula_ids]
    if not tracked:
        return "\n".join(
            [
                "## 🧪 标题公式反馈",
                "",
                "暂无文章记录最终公式 ID。新稿发布后会按“公式分类 × 平台 × 内容目标”汇总；单类少于 3 篇时只记录现象。",
            ]
        )

    grouped: dict[str, list[Article]] = {}
    for article in tracked:
        for category in sorted({formula_category(item) for item in article.formula_ids}):
            grouped.setdefault(category, []).append(article)

    lines = [
        "## 🧪 标题公式反馈",
        "",
        f"> 已追踪 {len(tracked)} / {len(articles)} 篇；同一标题组合多个公式时会进入多个分类。",
        "",
        "| 公式分类 | 样本 | 主要平台 | 内容目标 | 平均阅读 | 平均收藏率 | 结论边界 |",
        "|---|---:|---|---|---:|---:|---|",
    ]
    for category, items in sorted(grouped.items()):
        platforms = Counter(item.primary_platform for item in items)
        goals = Counter(item.content_goal for item in items)
        average_reads = round(sum(item.reads for item in items) / len(items))
        average_collect_rate = round(
            sum(item.collect_rate for item in items) / len(items),
            1,
        )
        boundary = "可做趋势比较" if len(items) >= 3 else "样本不足，只记录现象"
        lines.append(
            f"| {category} | {len(items)} | {platforms.most_common(1)[0][0]} | "
            f"{goals.most_common(1)[0][0]} | {average_reads:,} | "
            f"{average_collect_rate}% | {boundary} |"
        )
    return "\n".join(lines)


def generate_report(articles: list[Article]) -> str:
    today = date.today()
    max_reads = max((article.reads for article in articles), default=0)
    sorted_articles = sorted(articles, key=lambda item: item.reads, reverse=True)
    top_articles = sorted_articles[: min(3, len(sorted_articles))]
    bottom_articles = list(reversed(sorted_articles[-min(3, len(sorted_articles)) :]))
    accuracy_rows = aggregate_dimension_accuracy(articles)
    type_counts = Counter(article.type_name for article in articles)
    platform_counts = Counter(article.primary_platform for article in articles)
    published_dates = sorted(article.published_date for article in articles if article.published_date)
    leading_type = type_counts.most_common(1)[0][0] if type_counts else "暂无"
    leading_platform = platform_counts.most_common(1)[0][0] if platform_counts else "暂无"
    date_range = (
        f"{published_dates[0].isoformat()} ～ {published_dates[-1].isoformat()}"
        if published_dates
        else "暂无"
    )

    lines = [
        f"# {today.year}年{today.month:02d}月第{math.ceil(today.day / 7)}周 内容数据复盘",
        "",
        f"> 复盘日期：{today.isoformat()}",
        f"> 复盘范围：{len(articles)} 篇已填写有效阅读数据的文章",
        "",
        "## 📊 数据概览",
        "",
        build_overview_table(sorted_articles, max_reads),
        "",
        "## 🏆 红榜分析 (表现最好的前3名)",
        "",
    ]

    for index, article in enumerate(top_articles, start=1):
        lines.extend([build_top_section(article, index, max_reads), "", "---", ""])

    lines.extend(["## 📉 黑榜分析 (表现最差的后3名)", ""])

    for index, article in enumerate(bottom_articles, start=1):
        lines.extend([build_bottom_section(article, index), "", "---", ""])

    lines.extend(["## 🔄 7维度预判准确度", "", "> 对比发布前的7维度评估和实际数据表现，校准评估体系。", "", "| 维度 | 预判准确度 | 发现 |", "|------|-----------|------|"])
    for dimension, status, insight in accuracy_rows:
        lines.append(f"| **{dimension}** | {status} | {insight} |")

    lines.extend(["", build_formula_feedback(articles)])

    lines.extend(
        [
            "",
            "## 💡 方法论更新",
            "",
            "### 需要更新的规则",
            "",
            "- [ ] 根据红榜与黑榜的真实差异，判断是否需要更新标题、选题或开头规则",
            "- [ ] 只有连续多个样本支持同一结论时，才更新工作流权威源",
            "",
            "### 已执行的更新",
            "",
            "- 本脚本只生成复盘草案，不自动修改任何方法论或 Skill。",
            "",
            "## 📈 趋势观察",
            "",
            f"- **样本最多的内容类型**：{leading_type}（仅表示样本数量，不代表效果最好）",
            f"- **样本最多的平台**：{leading_platform}",
            f"- **样本发布时间范围**：{date_range}",
            "- **结论边界**：样本少于 3 篇时只记录现象，不更新通用规则。",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if has_flag("--help") or has_flag("-h"):
        print("用法：python scripts/generate-review-report.py [--output 数据统计/文件名.md]")
        print("仅纳入已发布且至少填写一个有效阅读量时间点的文章。")
        return

    articles = []
    published_count = 0
    for path in sorted(PUBLISHED_ROOT.rglob("*.md")):
        if not path.is_file():
            continue
        article = parse_article(path)
        if article:
            published_count += 1
            if article.reads > 0:
                articles.append(article)

    if not articles:
        print(
            f"复盘未生成：共 {published_count} 篇已发布文章，"
            "但没有文章填写有效阅读量。请先说“填数据”。"
        )
        raise SystemExit(2)

    report = generate_report(articles)
    output = read_arg("--output")
    if output:
        target = (ROOT / output).resolve() if not Path(output).is_absolute() else Path(output)
        write_text(target, report)
        print(f"已生成复盘文件：{target}")
    else:
        print(report)


if __name__ == "__main__":
    main()
