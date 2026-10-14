from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / name
    module_name = name.replace("-", "_").replace(".py", "") + "_test"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_unit(
    path: Path,
    unit_id: str,
    unit_type: str,
    relation: str = "",
    target: str = "",
    status: str = "candidate",
) -> None:
    path.write_text(
        f"""---
material_type: content_unit
unit_id: {unit_id}
unit_type: {unit_type}
---

## 关系

| 关系 | 目标 unit_id | 说明 | 状态 |
|---|---|---|---|
| {relation} | {target} | 测试关系 | {status} |
""",
        encoding="utf-8",
    )


def test_content_unit_audit_accepts_valid_graph(tmp_path: Path) -> None:
    audit = load_script("audit-content-units.py")
    write_unit(
        tmp_path / "问题.md",
        "CU-20260729-001",
        "question",
    )
    write_unit(
        tmp_path / "方案.md",
        "CU-20260729-002",
        "solution",
        "responds_to",
        "CU-20260729-001",
        "active",
    )
    report = audit.audit_units(tmp_path)
    assert report["units"] == 2
    assert report["errors"] == 0


def test_content_unit_audit_rejects_missing_active_target(tmp_path: Path) -> None:
    audit = load_script("audit-content-units.py")
    write_unit(
        tmp_path / "案例.md",
        "CU-20260729-003",
        "case",
        "proves",
        "CU-20260729-999",
        "active",
    )
    report = audit.audit_units(tmp_path)
    assert "unit.target_missing" in {
        finding["code"] for finding in report["findings"]
    }


def test_batch_plan_starts_read_only_and_uses_small_sample(tmp_path: Path) -> None:
    planner = load_script("plan-batch-expansion.py")
    target = tmp_path / "history"
    target.mkdir()
    for index in range(30):
        heading = "正文" if index < 27 else "旧版正文"
        (target / f"{index:02d}.md").write_text(
            f"---\ntitle: {index}\n---\n\n## {heading}\n\n内容\n",
            encoding="utf-8",
        )

    plan = planner.build_plan(target, workspace_root=tmp_path)
    assert plan["level"] == "L0_read_only_audit"
    assert plan["mutation_authorized"] is False
    assert len(plan["sample_files"]) == 3
    assert plan["structure_variants"] == 2
    assert all(len(batch) <= 20 for batch in plan["expansion_batches"])


def test_session_memory_guardrails_count_rejections_and_open_hypotheses(
    tmp_path: Path,
) -> None:
    dashboard = load_script("opening-dashboard.py")
    memory = tmp_path / "会话记忆.md"
    memory.write_text(
        """## 用户已否决的方向

| 日期 | 已否决方向 | 适用范围 | 否决依据 | 可重提条件 |
|---|---|---|---|---|
| 2026-07-29 | 不做泛工具清单 | 当前账号 | 缺少差异 | 用户重开 |

## 待验证假设

| 假设 ID | 假设 | 来源 | 验证方式 | 状态 | 验证结论 |
|---|---|---|---|---|---|
| H-01 | 清单更容易收藏 | 观察 | 连续测试三篇 | candidate | |
| H-02 | 教程更容易转发 | 数据 | 已验证 | verified | 通过 |
""",
        encoding="utf-8",
    )
    dashboard.SESSION_FILE = memory
    assert dashboard.memory_guardrail_counts() == (1, 1)
