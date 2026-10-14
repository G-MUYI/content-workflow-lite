from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from scripts.workflow_config import (
    DELIVERY_TAIL_WIP_LIMIT,
    NEXT_ACTION_STAGE_ORDER,
    ROUTE_RULES,
)


ROOT = Path(__file__).resolve().parents[1]


def load_dispatch_module():
    path = ROOT / "scripts" / "workflow-dispatch.py"
    spec = importlib.util.spec_from_file_location("workflow_dispatch_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_every_registered_trigger_matches_itself() -> None:
    dispatch = load_dispatch_module()
    for route in ROUTE_RULES:
        for trigger in route["triggers"]:
            assert dispatch.match_route(trigger) == route


def test_route_accepts_colon_or_space_payload_but_not_arbitrary_substring() -> None:
    dispatch = load_dispatch_module()
    assert dispatch.match_route("写：示例文章")["intent"] == "正文写作"
    assert dispatch.match_route("写 示例文章")["intent"] == "正文写作"
    assert dispatch.match_route("不要写") is None
    assert dispatch.match_route("检查标题") is None


def test_dispatch_generated_commands_are_routable(tmp_path: Path) -> None:
    dispatch = load_dispatch_module()
    dispatch.ROOT = tmp_path
    stages = [
        ("raw_idea", "", ""),
        ("topics_generated", "", ""),
        ("checked_in", "", ""),
        ("checked_in", "short_post", "short_post_first"),
        ("market_researched", "", ""),
        ("strategies_generated", "", ""),
        ("planned", "", ""),
        ("assets_ready", "", ""),
        ("drafted", "", ""),
        ("titled", "", ""),
        ("reviewed", "", ""),
    ]
    for index, (stage, content_form, recommended_path) in enumerate(stages):
        path = tmp_path / f"{index}.md"
        path.write_text("---\nstage: demo\n---\n", encoding="utf-8")
        item = dispatch.WorkflowFile(
            path=path,
            title="测试文章",
            stage=stage,
            priority="A",
            updated="2026-07-27",
            content_form=content_form,
            recommended_path=recommended_path,
            workflow_mode="",
        )
        action = dispatch.build_action(item)
        assert action["command"]
        assert dispatch.match_route(str(action["command"])) is not None, action


def test_standard_checked_in_can_plan_while_quick_can_write(tmp_path: Path) -> None:
    dispatch = load_dispatch_module()
    dispatch.ROOT = tmp_path
    path = tmp_path / "topic.md"
    path.write_text("---\nstage: checked_in\n---\n", encoding="utf-8")

    standard = dispatch.WorkflowFile(
        path=path,
        title="标准文章",
        stage="checked_in",
        priority="A",
        updated="2026-07-27",
        content_form="article",
        recommended_path="tutorial",
        workflow_mode="standard",
    )
    quick = dispatch.WorkflowFile(
        path=path,
        title="短篇",
        stage="checked_in",
        priority="A",
        updated="2026-07-27",
        content_form="short_post",
        recommended_path="short_post_first",
        workflow_mode="quick",
    )

    assert dispatch.build_action(standard)["blocked"] is False
    assert dispatch.build_action(standard)["next_stage"] == "strategies_generated"
    assert dispatch.build_action(quick)["blocked"] is False
    assert dispatch.build_action(quick)["next_stage"] == "drafted"


def test_tutorial_planned_action_requires_real_test_evidence(tmp_path: Path) -> None:
    dispatch = load_dispatch_module()
    dispatch.ROOT = tmp_path
    path = tmp_path / "tutorial.md"
    path.write_text("---\nstage: planned\n---\n", encoding="utf-8")
    item = dispatch.WorkflowFile(
        path=path,
        title="AI 绘图教程",
        stage="planned",
        priority="A",
        updated="2026-07-27",
        content_form="article",
        recommended_path="tutorial",
        workflow_mode="standard",
    )

    action = dispatch.build_action(item)
    assert action["blocked"] is False  # Evidence collection is executable, not yet passed.
    assert action["next_stage"] == "planned"
    assert action["target_stage"] == "assets_ready"
    assert "stage: planned" in path.read_text(encoding="utf-8")
    assert "实测任务包" in action["reason"]
    assert "至少 3 张关键截图" in action["reason"]


def test_next_action_order_pulls_work_toward_delivery() -> None:
    dispatch = load_dispatch_module()
    ranks = [dispatch.stage_rank(stage) for stage in NEXT_ACTION_STAGE_ORDER]
    assert ranks == sorted(ranks)
    assert dispatch.stage_rank("reviewed") < dispatch.stage_rank("titled")
    assert dispatch.stage_rank("titled") < dispatch.stage_rank("drafted")


def test_drafted_generates_candidates_without_faking_titled(tmp_path: Path) -> None:
    dispatch = load_dispatch_module()
    dispatch.ROOT = tmp_path
    path = tmp_path / "draft.md"
    path.write_text(
        "---\nstage: drafted\n---\n## 写作笔记\n\n### 风格自检\n\n"
        "- 风格档案是否已读取：是\n- 自检结论：像\n",
        encoding="utf-8",
    )
    item = dispatch.WorkflowFile(
        path=path,
        title="待起标题",
        stage="drafted",
        priority="A",
        updated="2026-08-31",
        content_form="article",
        recommended_path="opinion",
        workflow_mode="standard",
    )

    action = dispatch.build_action(item)
    assert action["blocked"] is False
    assert action["next_stage"] == "drafted"
    assert action["target_stage"] == "titled"
    assert "保持 drafted" in action["completion_condition"]


def test_existing_title_candidates_are_reused_for_authorized_selection(tmp_path: Path) -> None:
    dispatch = load_dispatch_module()
    dispatch.ROOT = tmp_path
    path = tmp_path / "draft.md"
    path.write_text(
        "---\nstage: drafted\n---\n"
        "## 写作笔记\n\n### 风格自检\n\n"
        "- 风格档案是否已读取：是\n- 自检结论：像\n\n"
        "## 标题备选\n\nXHS-001\nXHS-002\nXHS-003\nXHS-004\n",
        encoding="utf-8",
    )
    item = dispatch.WorkflowFile(
        path=path,
        title="已有候选",
        stage="drafted",
        priority="A",
        updated="2026-08-31",
        content_form="article",
        recommended_path="opinion",
        workflow_mode="standard",
    )

    action = dispatch.build_action(item)
    assert action["blocked"] is False
    assert action["command"] == "确认标题：已有候选"
    assert action["next_stage"] == "titled"
    assert "用户保留终选权时等待" in action["reason"]
    assert "stage: drafted" in path.read_text(encoding="utf-8")


def test_tail_wip_blocks_upstream_actions(tmp_path: Path) -> None:
    dispatch = load_dispatch_module()
    dispatch.ROOT = tmp_path
    dispatch.CONTENT_ROOT = tmp_path / "选题库"
    in_progress = dispatch.CONTENT_ROOT / "进行中"
    todo = dispatch.CONTENT_ROOT / "待写"
    in_progress.mkdir(parents=True)
    todo.mkdir(parents=True)

    for index in range(DELIVERY_TAIL_WIP_LIMIT):
        (in_progress / f"draft-{index}.md").write_text(
            "---\ntitle: 尾部内容\nstage: drafted\npriority: A\nupdated: 2026-08-31\n---\n"
            "## 写作笔记\n\n### 风格自检\n\n"
            "- 风格档案是否已读取：是\n- 自检结论：像\n",
            encoding="utf-8",
        )
    (todo / "upstream.md").write_text(
        "---\ntitle: 上游内容\nstage: market_researched\npriority: S\nupdated: 2026-08-31\n---\n",
        encoding="utf-8",
    )

    payload = dispatch.next_action_payload(limit=3)
    assert payload["wip_policy"]["active"] is True
    upstream = next(
        action for action in payload["blocked_actions"] if action["title"] == "上游内容"
    )
    assert "WIP 上限" in upstream["reason"]
    assert len(payload["actions"]) == DELIVERY_TAIL_WIP_LIMIT
    assert all(action["stage"] == "drafted" for action in payload["actions"])

    # Explicit scope survives global WIP limits; an unknown target never falls
    # back to selecting unrelated articles.
    route = dispatch.match_route("继续：上游内容")
    explicit = dispatch.build_payload("继续：上游内容", route)["dispatch"]
    assert explicit["wip_policy"]["active"] is False
    assert [a["title"] for a in explicit["actions"]] == ["上游内容"]
    missing = dispatch.next_action_payload(target="不存在的内容")
    assert missing["actions"] == []
    assert missing["selection_error"]


def test_repairable_style_gap_is_actionable_without_advancing_stage(tmp_path: Path) -> None:
    dispatch = load_dispatch_module()
    dispatch.ROOT = tmp_path
    path = tmp_path / "draft.md"
    original = "---\ntitle: 修复风格\nstage: drafted\n---\n## 正文\n原始正文\n"
    path.write_text(original, encoding="utf-8")
    item = dispatch.workflow_file(path)
    action = dispatch.build_action(item)
    assert action["blocked"] is False
    assert action["skill"] == "story-writer"
    assert action["target_stage"] == action["fallback_stage"] == "drafted"
    assert dispatch.build_run_contract([action], []) is not None
    assert path.read_text(encoding="utf-8") == original


def test_assets_confirmation_only_selects_named_file(tmp_path: Path) -> None:
    dispatch = load_dispatch_module()
    dispatch.ROOT = tmp_path
    dispatch.CONTENT_ROOT = tmp_path / "选题库"
    todo = dispatch.CONTENT_ROOT / "待写"
    todo.mkdir(parents=True)
    for title in ["甲", "乙"]:
        (todo / f"{title}.md").write_text(
            f"---\ntitle: {title}\nstage: planned\n---\n", encoding="utf-8"
        )
    command = "确认素材：乙"
    payload = dispatch.build_payload(command, dispatch.match_route(command))["dispatch"]
    assert [a["title"] for a in payload["actions"]] == ["乙"]
    assert payload["actions"][0]["next_stage"] == "planned"
    assert dispatch.assets_ready_payload(target="丙")["actions"] == []


def test_run_contract_names_scope_evidence_and_anti_cheat() -> None:
    dispatch = load_dispatch_module()
    actions = [
        {
            "title": "示例文章",
            "file": "选题库/待写/示例文章.md",
            "stage": "assets_ready",
            "next_stage": "drafted",
            "target_stage": "drafted",
            "fallback_stage": "assets_ready",
            "completion_condition": "正文已保存且实际 stage=drafted",
        }
    ]
    blocked = [{"reason": "大纲需要用户确认"}]
    contract = dispatch.build_run_contract(actions, blocked)

    assert contract is not None
    assert contract["scope"] == ["选题库/待写/示例文章.md"]
    assert "validate-workflow.py" in " ".join(contract["evidence"])
    assert "修改校验器" in " ".join(contract["forbidden"])
    assert contract["unknowns"] == ["大纲需要用户确认"]
    assert contract["targets"] == ["《示例文章》目标 stage=drafted"]
    assert "实际 stage=drafted" in contract["completion"][0]
    assert "stage=assets_ready" in contract["fallbacks"][0]
