#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from workflow_config import (
    DAILY_SOURCE_HARD_BLOCKERS,
    DAILY_SOURCE_PATH_GATES,
    DAILY_SOURCE_SCORE_DIMENSIONS,
    DAILY_SOURCE_SELECTION_THRESHOLD,
    DAILY_SOURCE_TIER_MODIFIERS,
)


def load_payload(input_path: str) -> dict[str, Any]:
    if input_path == "-":
        return json.load(sys.stdin)
    with Path(input_path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_score(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} 必须是 0-10 的数字")
    score = float(value)
    if not 0 <= score <= 10:
        raise ValueError(f"{name} 超出 0-10：{value}")
    return score


def score_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    candidate_id = str(candidate.get("id", "")).strip()
    title = str(candidate.get("title", "")).strip()
    if not candidate_id or not title:
        raise ValueError("每个候选必须包含非空 id 和 title")

    raw_scores = candidate.get("scores")
    if not isinstance(raw_scores, dict):
        raise ValueError(f"候选 {candidate_id} 缺少 scores 对象")

    scores: dict[str, float] = {}
    weighted_score = 0.0
    reasons: list[str] = []
    for key, contract in DAILY_SOURCE_SCORE_DIMENSIONS.items():
        if key not in raw_scores:
            raise ValueError(f"候选 {candidate_id} 缺少评分项：{key}")
        value = validate_score(key, raw_scores[key])
        scores[key] = value
        weighted_score += value / 10 * contract["weight"]
        minimum = float(contract["minimum"])
        if value < minimum:
            reasons.append(f"{contract['label']} {value:g} < {minimum:g}")

    source_tier = str(candidate.get("source_tier", "unknown")).strip()
    if source_tier not in DAILY_SOURCE_TIER_MODIFIERS:
        raise ValueError(
            f"候选 {candidate_id} 的 source_tier 无效：{source_tier}"
        )
    modifier = DAILY_SOURCE_TIER_MODIFIERS[source_tier]
    total = round(max(0.0, min(100.0, weighted_score + modifier)), 1)

    blockers = {
        str(item).strip()
        for item in candidate.get("blockers", [])
        if str(item).strip()
    }
    unknown_blockers = blockers - DAILY_SOURCE_HARD_BLOCKERS
    if unknown_blockers:
        raise ValueError(
            f"候选 {candidate_id} 含未知 blocker：{', '.join(sorted(unknown_blockers))}"
        )
    reasons.extend(f"硬阻塞：{item}" for item in sorted(blockers))

    path = str(candidate.get("recommended_path", "")).strip()
    for key, minimum in DAILY_SOURCE_PATH_GATES.get(path, {}).items():
        if scores[key] < minimum:
            label = DAILY_SOURCE_SCORE_DIMENSIONS[key]["label"]
            reasons.append(f"{path} 门槛：{label} {scores[key]:g} < {minimum:g}")

    if total < DAILY_SOURCE_SELECTION_THRESHOLD:
        reasons.append(
            f"总分 {total:g} < {DAILY_SOURCE_SELECTION_THRESHOLD}"
        )

    return {
        "id": candidate_id,
        "title": title,
        "recommended_path": path,
        "source_tier": source_tier,
        "scores": scores,
        "base_score": round(weighted_score, 1),
        "source_modifier": modifier,
        "total_score": total,
        "eligible": not reasons,
        "reasons": reasons,
    }


def rank_candidates(payload: dict[str, Any]) -> dict[str, Any]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("输入必须包含非空 candidates 数组")

    ranked = [score_candidate(candidate) for candidate in candidates]
    ranked.sort(
        key=lambda item: (
            not item["eligible"],
            -item["total_score"],
            -item["scores"]["evidence_readiness"],
            -item["scores"]["actionable_value"],
            -item["scores"]["information_gain"],
            item["id"],
        )
    )
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index

    selected = next((item for item in ranked if item["eligible"]), None)
    return {
        "selection_threshold": DAILY_SOURCE_SELECTION_THRESHOLD,
        "selected_id": selected["id"] if selected else None,
        "selected_title": selected["title"] if selected else None,
        "candidates": ranked,
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "| 排名 | 候选 | 需求 | 增量 | 交付 | 证据 | 时效 | 信源修正 | 总分 | 结论 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in result["candidates"]:
        scores = item["scores"]
        conclusion = "可选"
        if not item["eligible"]:
            conclusion = "排除：" + "；".join(item["reasons"])
        lines.append(
            "| {rank} | {title} | {audience_fit:g} | {information_gain:g} | "
            "{actionable_value:g} | {evidence_readiness:g} | {timeliness:g} | "
            "{source_modifier:+g} | {total_score:g} | {conclusion} |".format(
                conclusion=conclusion,
                **item,
                **scores,
            )
        )
    if result["selected_id"]:
        lines.append("")
        lines.append(
            f"**Top 1**：{result['selected_title']}（{result['selected_id']}）"
        )
    else:
        lines.append("")
        lines.append("**Top 1**：无，今天不强行出稿。")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="按工作流机器合同计算每日多来源选题排名"
    )
    parser.add_argument("--input", required=True, help="JSON 文件路径；- 表示 stdin")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = rank_candidates(load_payload(args.input))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"评分输入无效：{exc}", file=sys.stderr)
        return 2

    if args.format == "markdown":
        print(render_markdown(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
