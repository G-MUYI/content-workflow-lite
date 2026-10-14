from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_dispatch_module():
    path = ROOT / "scripts" / "workflow-dispatch.py"
    spec = importlib.util.spec_from_file_location("workflow_dispatch_behavior_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_trigger_eval_contract() -> None:
    dispatch = load_dispatch_module()
    cases = json.loads(
        (ROOT / "evals" / "trigger-eval.json").read_text(encoding="utf-8")
    )

    positives = sum(case["expected_intent"] is not None for case in cases)
    negatives = len(cases) - positives
    assert len(cases) >= 20
    assert positives >= 8
    assert negatives >= 8

    for case in cases:
        route = dispatch.match_route(case["query"])
        actual = route["intent"] if route else None
        assert actual == case["expected_intent"], case


def test_workflow_scenario_contract(tmp_path: Path) -> None:
    dispatch = load_dispatch_module()
    dispatch.ROOT = tmp_path
    cases = json.loads(
        (ROOT / "evals" / "workflow-scenarios.json").read_text(encoding="utf-8")
    )

    assert len(cases) >= 10
    for index, case in enumerate(cases):
        path = tmp_path / f"{index}.md"
        path.write_text(
            case.get("file_text", "---\nstage: placeholder\n---\n"),
            encoding="utf-8",
        )
        item = dispatch.WorkflowFile(
            path=path,
            title=case["name"],
            stage=case["stage"],
            priority="A",
            updated="2026-07-29",
            content_form=case.get("content_form", "article"),
            recommended_path=case.get("recommended_path", "opinion"),
            workflow_mode=case.get("workflow_mode", "standard"),
        )
        action = dispatch.build_action(item)
        for key, expected in case["expected"].items():
            assert action[key] == expected, case
        if case.get("reason_contains"):
            assert case["reason_contains"] in action["reason"], case
